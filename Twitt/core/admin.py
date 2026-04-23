from django.contrib import admin
from .models import OTP, Profile, Tweets, Hashtag


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('phone', 'code', 'created_at')
    search_fields = ('phone', 'code')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'phone', 'is_private', 'created_at')
    search_fields = ('name', 'phone', 'user__username')
    list_filter = ('is_private', 'created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Tweets)
class TweetsAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_preview', 'tweet_type', 'likes_count', 'comments_count', 'views_count',
                    'created_at')
    search_fields = ('content', 'user__username', 'user__profile__name')
    list_filter = ('tweet_type', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'likes_count', 'comments_count', 'views_count')

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    content_preview.short_description = 'محتوا'


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
