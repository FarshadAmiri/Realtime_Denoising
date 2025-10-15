from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from .models import StreamRecording, ActiveStream
from .webrtc_handler import create_session, get_session_by_username, close_session
from users.models import Friendship
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings


@login_required
def page_broadcaster(request):
    # Build friends list with streaming status
    user = request.user
    # Friends are accepted relationships in either direction
    outgoing_ids = list(
        Friendship.objects.filter(from_user=user, status='accepted').values_list('to_user_id', flat=True)
    )
    incoming_ids = list(
        Friendship.objects.filter(to_user=user, status='accepted').values_list('from_user_id', flat=True)
    )
    friend_ids = list(set(outgoing_ids + incoming_ids))
    friend_users = User.objects.filter(id__in=friend_ids)

    friends = []
    for fu in friend_users:
        friends.append({
            'username': fu.username,
            'is_streaming': ActiveStream.objects.filter(user=fu).exists(),
        })

    return render(request, 'streams/main.html', { 'friends': friends })


@login_required
def page_listener(request, username):
    # Use existing template from streams app with full context
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return render(request, 'streams/no_access.html', { 'username': username })

    is_owner = request.user.id == target_user.id
    # Enforce friendship for non-owners
    if not is_owner and not Friendship.are_friends(request.user, target_user):
        return render(request, 'streams/no_access.html', { 'username': username })

    is_streaming = ActiveStream.objects.filter(user=target_user).exists()
    recordings = StreamRecording.objects.filter(owner=target_user).order_by('-created_at')

    ctx = {
        'target_user': target_user,
        'is_owner': is_owner,
        'is_streaming': is_streaming,
        'recordings': recordings,
        'browser_audio_processing': getattr(settings, 'BROWSER_AUDIO_PROCESSING', True),
    }
    return render(request, 'streams/user_page.html', ctx)


# Compatibility views expected by audio_stream_project.urls
def main_page(request):
    """Serve the broadcaster page at root for quick testing."""
    return page_broadcaster(request)


def user_page(request, username):
    """Serve a simple listener page for the given username."""
    return page_listener(request, username)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_stream(request):
    user = request.user
    denoise = bool(request.data.get('denoise', True))
    # Close any lingering session first
    existing = get_session_by_username(user.username)
    if existing:
        async_to_sync(close_session)(existing.session_id)
    session = create_session(user.username, denoise=denoise)
    # Mark as active and broadcast presence
    ActiveStream.objects.update_or_create(
        user=user,
        defaults={
            'session_id': session.session_id,
            'denoise_enabled': denoise,
        },
    )
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'presence',
            {
                'type': 'streaming_status_update',
                'username': user.username,
                'is_streaming': True,
            },
        )
    except Exception:
        pass
    return Response({'session_id': session.session_id, 'denoise': denoise})


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_stream(request):
    user = request.user
    session = get_session_by_username(user.username)
    if not session:
        # Ensure ActiveStream is cleared and presence broadcasted even if session missing
        ActiveStream.objects.filter(user=user).delete()
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'presence',
                {
                    'type': 'streaming_status_update',
                    'username': user.username,
                    'is_streaming': False,
                },
            )
        except Exception:
            pass
        return Response({'stopped': True})
    async_to_sync(close_session)(session.session_id)
    # Clear ActiveStream and broadcast presence
    ActiveStream.objects.filter(user=user).delete()
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'presence',
            {
                'type': 'streaming_status_update',
                'username': user.username,
                'is_streaming': False,
            },
        )
    except Exception:
        pass
    return Response({'stopped': True})


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def webrtc_offer(request):
    user = request.user
    offer_sdp = request.data.get('sdp')
    if not offer_sdp:
        return Response({'error': 'SDP offer required'}, status=400)
    session = get_session_by_username(user.username)
    if not session:
        return Response({'error': 'No session'}, status=400)
    from asgiref.sync import async_to_sync
    try:
        answer_sdp = async_to_sync(session.handle_offer)(offer_sdp)
        return Response({'sdp': answer_sdp, 'type': 'answer', 'session_id': session.session_id})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def listener_offer(request, username):
    offer_sdp = request.data.get('sdp')
    if not offer_sdp:
        return Response({'error': 'SDP offer required'}, status=400)
    session = get_session_by_username(username)
    if not session:
        return Response({'error': 'User not streaming'}, status=400)
    from asgiref.sync import async_to_sync
    try:
        listener_id = f"{request.user.username}_{request.user.id}"
        answer_sdp = async_to_sync(session.create_listener_connection)(listener_id, offer_sdp)
        return Response({'sdp': answer_sdp, 'type': 'answer'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_recordings(request, username):
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    recs = StreamRecording.objects.filter(owner=user).order_by('-created_at')
    data = [{
        'id': r.id,
        'title': r.title,
        'file_url': r.file.url if r.file else None,
        'duration': r.duration,
        'created_at': r.created_at.isoformat(),
    } for r in recs]
    return Response(data)


# Backwards-compatible list endpoint mapped in project urls
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recordings_list(request, username=None):
    if username is None:
        username = request.user.username
    return user_recordings(request, username)


# Legacy endpoint placeholder; aiortc pipeline does not use chunk posts
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_audio_chunk(request):
    return Response({'status': 'ignored'})


@api_view(['GET'])
@permission_classes([AllowAny])
def stream_status(request, username):
    # Prefer DB-backed ActiveStream for status; fallback to in-memory session
    active = ActiveStream.objects.filter(user__username=username).exists()
    if not active:
        session = get_session_by_username(username)
        active = bool(session)
    return Response({'active': active})
    # End
