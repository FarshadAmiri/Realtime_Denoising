from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import uuid
import json

from .models import ActiveStream, StreamRecording
from users.models import Friendship


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_stream(request):
    """Start a new audio stream."""
    denoise = request.data.get('denoise', True)
    
    # Check if user already has an active stream
    existing = ActiveStream.objects.filter(user=request.user).first()
    if existing:
        return Response({'error': 'Stream already active'}, status=400)
    
    # Create new active stream
    session_id = uuid.uuid4()
    stream = ActiveStream.objects.create(
        user=request.user,
        session_id=session_id,
        denoise_enabled=denoise
    )
    
    # Broadcast presence update
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "presence",
        {
            "type": "streaming_status_update",
            "username": request.user.username,
            "is_streaming": True,
        }
    )
    
    return Response({
        'session_id': str(session_id),
        'status': 'started'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_stream(request):
    """Stop the current audio stream and save recording."""
    try:
        stream = ActiveStream.objects.get(user=request.user)
        
        # Get recording info from request (if any)
        duration = request.data.get('duration', 0.0)
        
        # Create recording entry (file would be uploaded separately in full implementation)
        from datetime import datetime
        title = f"Stream {stream.started_at.strftime('%Y-%m-%d %H:%M')}"
        
        # Note: In a full implementation, the audio file would be saved by the
        # AudioProcessor and the path passed here. For now, we create a placeholder.
        recording = StreamRecording.objects.create(
            owner=request.user,
            title=title,
            duration=duration,
            denoise_enabled=stream.denoise_enabled,
        )
        
        # Delete active stream
        stream.delete()
        
        # Broadcast presence update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "presence",
            {
                "type": "streaming_status_update",
                "username": request.user.username,
                "is_streaming": False,
            }
        )
        
        return Response({
            'status': 'stopped',
            'recording_id': recording.id,
        })
    except ActiveStream.DoesNotExist:
        return Response({'error': 'No active stream'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stream_status(request, username):
    """Get streaming status for a user."""
    try:
        user = User.objects.get(username=username)
        is_streaming = ActiveStream.objects.filter(user=user).exists()
        
        if is_streaming:
            stream = ActiveStream.objects.get(user=user)
            return Response({
                'is_streaming': True,
                'session_id': str(stream.session_id),
                'started_at': stream.started_at.isoformat(),
                'denoise_enabled': stream.denoise_enabled,
            })
        else:
            return Response({'is_streaming': False})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_audio_chunk(request):
    """
    Save audio chunk data (for WebRTC streaming).
    
    In a full implementation, this would receive audio data from the broadcaster,
    process it through AudioProcessor, and fan out to listeners.
    """
    try:
        session_id = request.data.get('session_id')
        audio_data = request.data.get('audio_data')  # Base64 encoded audio
        
        # Verify user has active stream
        stream = ActiveStream.objects.get(user=request.user, session_id=session_id)
        
        # In full implementation:
        # 1. Decode audio data
        # 2. Process through AudioProcessor
        # 3. Fan out to listeners via WebSocket
        # 4. Store in recording buffer
        
        return Response({'status': 'received'})
        
    except ActiveStream.DoesNotExist:
        return Response({'error': 'No active stream'}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recordings_list(request, username=None):
    """List recordings for a user."""
    if username:
        # Get recordings for specific user
        target_user = get_object_or_404(User, username=username)
        
        # Check if requester can view (owner or friend)
        if request.user != target_user:
            if not Friendship.are_friends(request.user, target_user):
                return Response({'error': 'Not authorized'}, status=403)
        
        recordings = StreamRecording.objects.filter(owner=target_user)
    else:
        # Get own recordings
        recordings = StreamRecording.objects.filter(owner=request.user)
    
    data = [{
        'id': r.id,
        'title': r.title,
        'duration': r.duration,
        'duration_display': r.get_duration_display(),
        'file_url': r.file.url if r.file else None,
        'created_at': r.created_at.isoformat(),
        'denoise_enabled': r.denoise_enabled,
    } for r in recordings]
    
    return Response({'recordings': data})


@login_required
def main_page(request):
    """Main page with friends list and stream interface."""
    from django.db.models import Q
    
    # Get user's friends
    friendships = Friendship.objects.filter(
        Q(from_user=request.user, status='accepted') |
        Q(to_user=request.user, status='accepted')
    ).select_related('from_user', 'to_user')
    
    friends = []
    for friendship in friendships:
        friend = friendship.to_user if friendship.from_user == request.user else friendship.from_user
        is_streaming = ActiveStream.objects.filter(user=friend).exists()
        friends.append({
            'username': friend.username,
            'is_streaming': is_streaming,
        })
    
    return render(request, 'streams/main.html', {
        'friends': friends,
    })


@login_required
def user_page(request, username):
    """User/friend page showing their stream and recordings."""
    target_user = get_object_or_404(User, username=username)
    
    # Check access
    is_owner = request.user == target_user
    is_friend = Friendship.are_friends(request.user, target_user)
    
    if not is_owner and not is_friend:
        return render(request, 'streams/no_access.html', {'username': username})
    
    # Get stream status
    is_streaming = ActiveStream.objects.filter(user=target_user).exists()
    
    # Get recordings
    recordings = StreamRecording.objects.filter(owner=target_user)
    
    return render(request, 'streams/user_page.html', {
        'target_user': target_user,
        'is_owner': is_owner,
        'is_streaming': is_streaming,
        'recordings': recordings,
    })
