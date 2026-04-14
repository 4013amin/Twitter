from django.urls import path
from . import views
from django.urls import re_path
from . import consumers

app_name = 'chat'

urlpatterns = [
    path('', views.chat_room, name='chat'),
    path('<str:username>/', views.chat_room, name='chat_room'),
    path('send/', views.send_message, name='send_message'),

    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),

    path('message/<int:message_id>/delete-for-me/', views.delete_message_for_me, name='delete_message_for_me'),

    path('conversation/<str:username>/delete/', views.delete_conversation, name='delete_conversation'),
]

websocket_urlpatterns = [
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
]
