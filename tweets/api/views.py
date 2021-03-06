from django.utils.decorators import method_decorator
from newsfeeds.services import NewsFeedService
from ratelimit.decorators import ratelimit
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from tweets.api.serializers import (
    TweetSerializer,
    TweetSerializerForCreate,
    TweetSerializerForDetail,
)
from tweets.models import Tweet
from tweets.services import TweetService
from utils.decorators import required_params
from utils.paginations import EndlessPagination


class TweetViewSet(viewsets.GenericViewSet):
    serializer_class = TweetSerializerForCreate
    queryset = Tweet.objects.all()
    pagination_class = EndlessPagination

    def get_permissions(self):
        # action - the name of the current action (e.g., list, create).
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]


    @required_params(params=['user_id'])
    @method_decorator(ratelimit(key='user_or_ip', rate='5/s', method='GET', block=True))
    def list(self, request): # get tweets without logging in
        # if 'user_id' not in request.query_params:
        #     return Response({'error': 'missing user_id'}, status=400)

        user_id = request.query_params['user_id']
        cached_tweets_list = TweetService.get_cached_tweets(user_id)
        tweets = self.paginator.paginated_cached_list_in_redis(cached_tweets_list, request)
        if tweets is None:
            # order_by cannot add to paginate_queryset
            queryset = Tweet.objects.filter(user_id=user_id).order_by('-created_at')
            tweets = self.paginate_queryset(queryset)

        serializer = TweetSerializer(
            tweets,
            context={'request': request},
            many=True,
        )

        return self.get_paginated_response(serializer.data)

    @method_decorator(ratelimit(key='user_or_ip', rate='5/s', method='GET', block=True))
    def retrieve(self, request, *args, **kwargs):
        tweet = self.get_object()
        return Response(
            TweetSerializerForDetail(tweet, context={'request': request}).data,
            status=status.HTTP_200_OK
        )

    @method_decorator(ratelimit(key='user', rate='1/s', method='POST', block=True))
    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def create(self, request):
        serializer = TweetSerializerForCreate(
            data=request.data,
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Please check input.',
                'errors': serializer.errors
            }, status=400)
        tweet = serializer.save() # call create method in TweetSerializerForCreate
        NewsFeedService.fanout_to_followers(tweet)

        return Response(
            TweetSerializer(tweet, context={'request': request}).data,
            status=201
        )