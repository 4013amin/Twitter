import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TwitterConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'tweets_room'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print(f"✅ کاربر {self.scope['user']} وصل شد")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(f"❌ کاربر از اتاق خارج شد: {self.channel_name}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'new_tweet':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'tweet_update',
                    'tweet_id': data.get('tweet_id'),
                    'content': data.get('content'),
                    'user': data.get('username'),
                }
            )

    async def tweet_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'tweet_update',
            'tweet_id': event['tweet_id'],
            'content': event['content'],
            'user': event['user'],
        }))


class TweetActivityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'tweet_activities'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print(f"✅ WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):  # ✅ اضافه شد: async
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(f"❌ WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        print(f"📩 Received: {data}")

    async def tweet_like_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'like_update',
            'tweet_id': event['tweet_id'],
            'likes_count': event['likes_count'],
            'liked': event['liked'],
            'username': event['username'],
        }))

    async def tweet_comment_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment_update',
            'tweet_id': event['tweet_id'],
            'comments_count': event['comments_count'],
            'new_comment': event.get('new_comment'),
            'username': event['username'],
        }))

    async def tweet_comment_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment_deleted',
            'tweet_id': event['tweet_id'],
            'comments_count': event['comments_count'],
            'comment_id': event['comment_id'],
            'username': event['username'],
        }))
