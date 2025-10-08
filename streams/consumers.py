import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class PresenceConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for tracking user presence and streaming status."""
    
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        self.user = self.scope["user"]
        self.presence_group = "presence"
        
        # Join presence group
        await self.channel_layer.group_add(
            self.presence_group,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current friends' status
        friends_status = await self.get_friends_status()
        await self.send(text_data=json.dumps({
            'type': 'friends_status',
            'friends': friends_status
        }))
    
    async def disconnect(self, close_code):
        if hasattr(self, 'presence_group'):
            await self.channel_layer.group_discard(
                self.presence_group,
                self.channel_name
            )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')
        
        if msg_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
    
    async def streaming_status_update(self, event):
        """Receive streaming status updates from group."""
        await self.send(text_data=json.dumps({
            'type': 'streaming_status',
            'username': event['username'],
            'is_streaming': event['is_streaming']
        }))
    
    @database_sync_to_async
    def get_friends_status(self):
        """Get status of all friends."""
        from users.models import Friendship
        
        # Get all friends
        friendships = Friendship.objects.filter(
            user1=self.user
        ).select_related('user2') | Friendship.objects.filter(
            user2=self.user
        ).select_related('user1')
        
        friends_status = []
        for friendship in friendships:
            friend = friendship.user2 if friendship.user1 == self.user else friendship.user1
            friends_status.append({
                'username': friend.username,
                'is_streaming': friend.is_streaming,
            })
        
        return friends_status


class StreamConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for signaling and control messages for streaming."""
    
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        self.user = self.scope["user"]
        self.stream_username = self.scope['url_route']['kwargs']['username']
        self.stream_room = f"stream_{self.stream_username}"
        
        # Check if users are friends
        are_friends = await self.check_friendship()
        if not are_friends and self.user.username != self.stream_username:
            await self.close()
            return
        
        # Join stream room
        await self.channel_layer.group_add(
            self.stream_room,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'stream_room'):
            await self.channel_layer.group_discard(
                self.stream_room,
                self.channel_name
            )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')
        
        if msg_type == 'offer':
            # Forward WebRTC offer to the stream room
            await self.channel_layer.group_send(
                self.stream_room,
                {
                    'type': 'webrtc_offer',
                    'offer': data.get('offer'),
                    'from_user': self.user.username
                }
            )
        elif msg_type == 'answer':
            # Forward WebRTC answer
            await self.channel_layer.group_send(
                self.stream_room,
                {
                    'type': 'webrtc_answer',
                    'answer': data.get('answer'),
                    'from_user': self.user.username
                }
            )
        elif msg_type == 'ice_candidate':
            # Forward ICE candidate
            await self.channel_layer.group_send(
                self.stream_room,
                {
                    'type': 'ice_candidate',
                    'candidate': data.get('candidate'),
                    'from_user': self.user.username
                }
            )
    
    async def webrtc_offer(self, event):
        """Send WebRTC offer to client."""
        await self.send(text_data=json.dumps({
            'type': 'offer',
            'offer': event['offer'],
            'from_user': event['from_user']
        }))
    
    async def webrtc_answer(self, event):
        """Send WebRTC answer to client."""
        await self.send(text_data=json.dumps({
            'type': 'answer',
            'answer': event['answer'],
            'from_user': event['from_user']
        }))
    
    async def ice_candidate(self, event):
        """Send ICE candidate to client."""
        await self.send(text_data=json.dumps({
            'type': 'ice_candidate',
            'candidate': event['candidate'],
            'from_user': event['from_user']
        }))
    
    @database_sync_to_async
    def check_friendship(self):
        """Check if current user and stream owner are friends."""
        from users.models import Friendship
        
        if self.user.username == self.stream_username:
            return True
        
        try:
            streamer = User.objects.get(username=self.stream_username)
        except User.DoesNotExist:
            return False
        
        return Friendship.objects.filter(
            user1=self.user, user2=streamer
        ).exists() or Friendship.objects.filter(
            user1=streamer, user2=self.user
        ).exists()
