from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import StreamRecording, ActiveStream
from .webrtc_handler import create_session, get_session, get_session_by_username, close_session
from users.models import User, Friendship


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_stream(request):
    """Start a new streaming session."""
    user = request.user
    
    # Check if user already has an active stream
    existing_session = get_session_by_username(user.username)
    if existing_session:
        return Response(
            {'error': 'Stream already active'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create new session
    session = create_session(user.username)
    
    # Update user streaming status
    user.is_streaming = True
    user.save()
    
    # Create ActiveStream record
    ActiveStream.objects.update_or_create(
        user=user,
        defaults={'session_id': session.session_id}
    )
    
    # Notify friends via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "presence",
        {
            'type': 'streaming_status_update',
            'username': user.username,
            'is_streaming': True
        }
    )
    
    return Response({
        'session_id': session.session_id,
        'message': 'Stream started'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_stream(request):
    """Stop the current streaming session."""
    user = request.user
    
    # Get active stream
    try:
        active_stream = ActiveStream.objects.get(user=user)
        session_id = active_stream.session_id
        
        # Close WebRTC session
        asyncio.run(close_session(session_id))
        
        # Delete active stream record
        active_stream.delete()
        
        # Update user streaming status
        user.is_streaming = False
        user.save()
        
        # Notify friends
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "presence",
            {
                'type': 'streaming_status_update',
                'username': user.username,
                'is_streaming': False
            }
        )
        
        return Response({'message': 'Stream stopped'})
    except ActiveStream.DoesNotExist:
        return Response(
            {'error': 'No active stream'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def webrtc_offer(request):
    """Handle WebRTC offer from broadcaster."""
    user = request.user
    offer_sdp = request.data.get('sdp')
    
    if not offer_sdp:
        return Response(
            {'error': 'SDP offer required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get or create session
    session = get_session_by_username(user.username)
    if not session:
        return Response(
            {'error': 'No active stream session'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Handle offer asynchronously
    try:
        answer_sdp = asyncio.run(session.handle_offer(offer_sdp))
        return Response({
            'sdp': answer_sdp,
            'type': 'answer',
            'session_id': session.session_id
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def listener_offer(request, username):
    """Handle WebRTC offer from a listener wanting to hear a stream."""
    user = request.user
    offer_sdp = request.data.get('sdp')
    
    if not offer_sdp:
        return Response(
            {'error': 'SDP offer required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if streamer exists and is streaming
    try:
        streamer = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if they are friends
    are_friends = Friendship.objects.filter(
        user1=user, user2=streamer
    ).exists() or Friendship.objects.filter(
        user1=streamer, user2=user
    ).exists()
    
    if not are_friends and user != streamer:
        return Response(
            {'error': 'Not friends with this user'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get session
    session = get_session_by_username(username)
    if not session:
        return Response(
            {'error': 'User is not streaming'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create listener connection
    try:
        listener_id = f"{user.username}_{user.id}"
        answer_sdp = asyncio.run(session.create_listener_connection(listener_id, offer_sdp))
        return Response({
            'sdp': answer_sdp,
            'type': 'answer'
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_recordings(request, username):
    """Get recordings for a specific user."""
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if they are friends or same user
    requester = request.user
    are_friends = Friendship.objects.filter(
        user1=requester, user2=user
    ).exists() or Friendship.objects.filter(
        user1=user, user2=requester
    ).exists()
    
    if not are_friends and requester != user:
        return Response(
            {'error': 'Not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    recordings = StreamRecording.objects.filter(owner=user)
    
    data = [{
        'id': rec.id,
        'title': rec.title,
        'file_url': request.build_absolute_uri(rec.file.url) if rec.file else None,
        'duration': rec.duration,
        'created_at': rec.created_at.isoformat(),
    } for rec in recordings]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stream_status(request, username):
    """Check if a user is currently streaming."""
    try:
        user = User.objects.get(username=username)
        return Response({
            'username': username,
            'is_streaming': user.is_streaming
        })
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
