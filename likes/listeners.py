def incr_likes_count(sender, instance, created, **kwargs):
    from django.db.models import F
    from comments.models import Comment
    from tweets.models import Tweet
    # only creating new likes will update likes_count
    if not created:
        return

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        Comment.objects.filter(id=instance.object_id).update(likes_count=F('likes_count') + 1)
        return

    # F has row lock to solve concurrent issues (many likes at the same time).
    # .update will not trigger post_save listener
    Tweet.objects.filter(id=instance.object_id).update(likes_count=F('likes_count') + 1)

def decr_likes_count(sender, instance, **kwargs):
    from django.db.models import F
    from comments.models import Comment
    from tweets.models import Tweet

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        Comment.objects.filter(id=instance.object_id).update(likes_count=F('likes_count') - 1)
        return

    # F has row lock to solve concurrent issues (many likes at the same time).
    Tweet.objects.filter(id=instance.object_id).update(likes_count=F('likes_count') - 1)