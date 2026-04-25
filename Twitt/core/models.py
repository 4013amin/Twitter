import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# Create your models here.

class OTP(models.Model):
    phone = models.CharField(max_length=11, unique=True)
    code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.phone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=11)
    image = models.ImageField(upload_to='profile_pics', blank=True, null=True)
    bio = models.TextField()
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


class Tweets(models.Model):
    TWEET_TYPE_CHOICES = [
        ('text', 'متنی'),
        ('image', 'تصویر'),
        ('voice', 'ویس'),
        ('video', 'ویدیو'),

    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tweets')
    content = models.TextField()
    tweet_type = models.CharField(max_length=10, choices=TWEET_TYPE_CHOICES)

    # Hashtag
    hashtag = models.ForeignKey('Hashtag', on_delete=models.CASCADE, related_name='tweets', null=True, blank=True)

    # File
    image = models.ImageField(upload_to='image_posts', blank=True, null=True)
    voice = models.FileField(upload_to='tweet_voices', blank=True, null=True)
    video = models.FileField(upload_to='tweet_videos', blank=True, null=True)

    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    # آمار
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}..."

    @property
    def is_reply(self):
        return self.parent is not None

    @property
    def is_edit(self):
        if not self.created_at:
            return False

        time_diff = timezone.now() - self.created_at
        return time_diff <= datetime.timedelta(minutes=30)

    # Hashtag
    def extract_and_save_hashtags(self):
        import re
        hashtag_name = re.findall(r'#\w+', self.content)
        for name in hashtag_name:
            hashtag, create = Hashtag.objects.get_or_create(name=name)
            if not self.hashtag.filter(id=hashtag.id).exists():
                self.hashtag.add(hashtag)
                hashtag.tweet_count += 1
                hashtag.last_used = timezone.now()
                hashtag.save()


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    tweet = models.ForeignKey('Tweets', on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tweet')


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    tweet = models.ForeignKey('Tweets', on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.content[:20]}..."


# Follow
class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        indexes = [
            models.Index(fields=['follower', 'created_at']),
            models.Index(fields=['following', 'created_at']),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class Hashtag(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    tweet_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name
