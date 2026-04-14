import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.db.models import Q
from . import models


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_group_name = 'chat_room'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action', 'send')

        if action == 'delete_message':
            await self.handle_delete_message(data)
        elif action == 'delete_conversation':
            await self.handle_delete_conversation(data)
        elif action == 'send':
            await self.handle_send_message(data)

    async def handle_send_message(self, data):
        message_text = data.get('message', '').strip()
        receiver_id = data.get('receiver_id')
        reply_to_id = data.get('reply_to_id')
        sender = self.scope['user']

        if sender.is_authenticated and message_text and receiver_id:
            msg = await self.save_message(sender.id, receiver_id, message_text, reply_to_id)

            reply_data = None
            if msg.reply_to:
                reply_data = {
                    'id': msg.reply_to.id,
                    'message': msg.reply_to.message[:50],
                    'sender': msg.reply_to.sender.username,
                }

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'action': 'new_message',
                    'message': message_text,
                    'sender': sender.username,
                    'sender_id': sender.id,
                    'receiver_id': receiver_id,
                    'message_id': msg.id,
                    'time': msg.time.strftime('%H:%M'),
                    'reply_to': reply_data,
                }
            )

    async def handle_delete_message(self, data):
        message_id = data.get('message_id')
        sender = self.scope['user']

        if not sender.is_authenticated:
            return

        deleted = await self.delete_message(message_id, sender.id)
        if deleted:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'action': 'message_deleted',
                    'message_id': message_id,
                    'sender_id': sender.id,
                }
            )

    async def handle_delete_conversation(self, data):
        username = data.get('username')
        sender = self.scope['user']

        if not sender.is_authenticated:
            return

        deleted_ids = await self.delete_full_conversation(username)
        if deleted_ids:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'action': 'conversation_deleted',
                    'deleted_ids': deleted_ids,
                    'username': username,
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, message, reply_to_id=None):
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)
        reply_to = None
        if reply_to_id:
            reply_to = models.ChatMessage.objects.get(id=reply_to_id)
        return models.ChatMessage.objects.create(
            sender=sender,
            receiver=receiver,
            message=message,
            reply_to=reply_to
        )

    @database_sync_to_async
    def delete_message(self, message_id, user_id):
        try:
            msg = models.ChatMessage.objects.get(id=message_id, sender_id=user_id)
            msg.delete()
            return True
        except models.ChatMessage.DoesNotExist:
            return False

    @database_sync_to_async
    def delete_full_conversation(self, username):
        try:
            other_user = User.objects.get(username=username)
            messages = models.ChatMessage.objects.filter(
                Q(sender=self.scope['user'], receiver=other_user) |
                Q(sender=other_user, receiver=self.scope['user'])
            )
            deleted_ids = list(messages.values_list('id', flat=True))
            messages.delete()
            return deleted_ids
        except User.DoesNotExist:
            return []