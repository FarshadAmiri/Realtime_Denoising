import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ActiveStream


class PresenceConsumer(AsyncWebsocketConsumer):
    """Handles presence updates for streaming status."""
    
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        # Join presence group
        self.presence_group = "presence"
        await self.channel_layer.group_add(
            self.presence_group,
            self.channel_name
        )
        await self.accept()
        
        # Send current streaming statuses to the newly connected user
        await self.send_all_streaming_statuses()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'presence_group'):
            await self.channel_layer.group_discard(
                self.presence_group,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming messages (for polling fallback)."""
        data = json.loads(text_data)
        action = data.get('action')
        
        if action == 'get_status':
            # Send current streaming statuses
            await self.send_all_streaming_statuses()
    
    async def streaming_status_update(self, event):
        """Broadcast streaming status updates."""
        await self.send(text_data=json.dumps({
            'type': 'streaming_status_update',
            'username': event['username'],
            'is_streaming': event['is_streaming'],
        }))
    
    async def online_status_update(self, event):
        """Broadcast online/offline status updates."""
        await self.send(text_data=json.dumps({
            'type': 'online_status_update',
            'username': event['username'],
            'is_online': event['is_online'],
        }))
    
    async def stream_ended(self, event):
        """Broadcast stream ended notification."""
        await self.send(text_data=json.dumps({
            'type': 'stream_ended',
            'username': event['username'],
        }))
    
    async def recording_saved(self, event):
        """Broadcast new recording saved notification."""
        await self.send(text_data=json.dumps({
            'type': 'recording_saved',
            'username': event['username'],
            'recording': event.get('recording', {}),
        }))
    
    @database_sync_to_async
    def get_streaming_users(self):
        """Get all currently streaming users."""
        active_streams = ActiveStream.objects.select_related('user').all()
        return [stream.user.username for stream in active_streams]
    
    async def send_all_streaming_statuses(self):
        """Send all current streaming statuses."""
        streaming_users = await self.get_streaming_users()
        await self.send(text_data=json.dumps({
            'type': 'all_statuses',
            'streaming_users': streaming_users,
        }))


class StreamConsumer(AsyncWebsocketConsumer):
    """Handles WebRTC signaling for audio streaming."""
    
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        self.username = self.scope['url_route']['kwargs']['username']
        self.stream_group = f"stream_{self.username}"
        
        # Verify user is friend or owner
        can_access = await self.can_access_stream()
        if not can_access:
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.stream_group,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'stream_group'):
            await self.channel_layer.group_discard(
                self.stream_group,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle WebRTC signaling messages."""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        # Broadcast to all listeners in the stream group
        await self.channel_layer.group_send(
            self.stream_group,
            {
                'type': 'webrtc_signal',
                'message': data,
                'sender': self.scope["user"].username,
            }
        )
    
    async def webrtc_signal(self, event):
        """Forward WebRTC signals to the client."""
        # Don't send back to sender
        if event['sender'] != self.scope["user"].username:
            await self.send(text_data=json.dumps(event['message']))
    
    @database_sync_to_async
    def can_access_stream(self):
        """Check if user can access this stream."""
        from users.models import Friendship
        
        current_user = self.scope["user"]
        
        # Owner can always access
        if current_user.username == self.username:
            return True
        
        # Check if they are friends
        try:
            target_user = User.objects.get(username=self.username)
            return Friendship.are_friends(current_user, target_user)
        except User.DoesNotExist:
            return False
