from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
from . import consumers

urlpatterns = [
    path('', views.home, name='home'),
    path('request-otpv/', views.request_otp_view, name='request_otpvi'),
    path('verify-otp/<str:phone>/', views.verify_otp_view, name='verify_otp'),
    path('setup-profile/', views.setup_profile, name='setup_profile'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='user_profile'),

    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('create-tweet/', views.create_tweet, name='create_tweet'),
    path('edit-tweet/<int:tweet_id>/', views.edit_tweet, name='edit_tweet'),
    path('tweet/<int:tweet_id>/', views.tweet_detail, name='tweet_detail'),
    path('tweet/<int:tweet_id>/reply/', views.create_reply, name='create_reply'),
    path('tweet_delete/<int:tweet_id>/', views.delete_reply, name='delete_reply'),

    path('tweet/<int:tweet_id>/delete/', views.delete_tweet, name='delete_tweet'),
    path('tweet/<int:tweet_id>/like/', views.like_tweet, name='like_tweet'),
    path('tweet/<int:tweet_id>/comment/', views.add_comment, name='add_comment'),
    path('tweet/<int:tweet_id>/delete_comment/', views.delete_comment, name='delete_comment'),

    path('search/', views.search_view, name='search'),

    # Follow
    path('follow/<int:user_id>/', views.follow_users, name='follow_user'),
    path('unfollow/<int:user_id>/', views.unfollow_users, name='unfollow_user'),
    path('toggle-follow/<int:user_id>/', views.toggle_follow, name='toggle_follow'),
    path('<int:user_id>/followers/', views.followers_list, name='followers_list'),
    path('<int:user_id>/following/', views.following_list, name='following_list'),

    path('logout/', views.logout_view, name='logout'),
]

websocket_urlpatterns = [
    path('ws/tweets/', consumers.TwitterConsumer.as_asgi()),
    path('ws/tweet-activity/', consumers.TweetActivityConsumer.as_asgi()),
]
