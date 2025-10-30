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
from .presence_store import set_online, is_online


@login_required
def page_broadcaster(request):
    # Build friends list with streaming status
    user = request.user
    # Mark viewer online immediately for initial render accuracy
    try:
        set_online(user.username)
    except Exception:
        pass
    
    # Check if user is admin
    is_admin = user.is_superuser or (hasattr(user, 'profile') and user.profile.user_level == 'admin')
    
    if is_admin:
        # Admins see all users except themselves
        friend_users = User.objects.exclude(id=user.id).order_by('username')
    else:
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
            'is_online': is_online(fu.username),
        })

    # Use in-memory session as the primary source of truth
    from .webrtc_handler import get_session_by_username
    self_is_streaming = bool(get_session_by_username(user.username))
    self_is_online = is_online(user.username)
    
    # Check if user can stream
    can_stream = True
    if hasattr(user, 'profile'):
        can_stream = user.profile.can_stream()

    return render(request, 'streams/main.html', {
        'friends': friends,
        'self_is_streaming': self_is_streaming,
        'self_is_online': self_is_online,
        'can_stream': can_stream,
        'browser_audio_processing': getattr(settings, 'BROWSER_AUDIO_PROCESSING', True),
    })


@login_required
def page_listener(request, username):
    # Use existing template from streams app with full context
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return render(request, 'streams/no_access.html', { 'username': username })

    is_owner = request.user.id == target_user.id
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.user_level == 'admin')
    
    # Enforce friendship for non-owners (unless admin)
    if not is_owner and not is_admin and not Friendship.are_friends(request.user, target_user):
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
    if request.user.is_authenticated and request.user.username == username:
        # For own page, send to SPA main page
        return main_page(request)
    return page_listener(request, username)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_stream(request):
    user = request.user
    
    # Check if user is allowed to stream
    if hasattr(user, 'profile'):
        if not user.profile.can_stream():
            return Response({'error': 'You do not have permission to stream'}, status=403)
    
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
        # Broadcast both streaming stopped and stream ended notification
        async_to_sync(channel_layer.group_send)(
            'presence',
            {
                'type': 'streaming_status_update',
                'username': user.username,
                'is_streaming': False,
            },
        )
        async_to_sync(channel_layer.group_send)(
            'presence',
            {
                'type': 'stream_ended',
                'username': user.username,
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


def _recordings_data_for_user(user):
    recs = StreamRecording.objects.filter(owner=user).order_by('-created_at')
    data = []
    for r in recs:
        file_url = None
        if getattr(r, 'file', None):
            try:
                if r.file.name and r.file.storage.exists(r.file.name):
                    file_url = r.file.url
            except Exception:
                file_url = None
        data.append({
            'id': r.id,
            'title': r.title,
            'file_url': file_url,
            'duration': r.duration,
            'created_at': r.created_at.isoformat(),
        })
    return data


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_recordings(request, username):
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    return Response(_recordings_data_for_user(user))


# Backwards-compatible list endpoint mapped in project urls
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recordings_list(request, username=None):
    if username is None:
        username = request.user.username
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    return Response(_recordings_data_for_user(user))


# Legacy endpoint placeholder; aiortc pipeline does not use chunk posts
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_audio_chunk(request):
    return Response({'status': 'ignored'})


@api_view(['GET'])
@permission_classes([AllowAny])
def stream_status(request, username):
    # Authoritative live status is in-memory session; DB can be stale
    session = get_session_by_username(username)
    active = bool(session)
    if not active:
        # Best-effort cleanup of stale DB row so other views don't misreport
        ActiveStream.objects.filter(user__username=username).delete()
    online = is_online(username)
    return Response({'active': active, 'online': online})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def heartbeat(request):
    """Mark current user as online (called periodically by client)."""
    username = request.user.username
    was_online = is_online(username)
    set_online(username)
    # Broadcast online status if state changed (first heartbeat or returning after timeout)
    if not was_online:
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'presence',
                {
                    'type': 'online_status_update',
                    'username': username,
                    'is_online': True,
                },
            )
        except Exception:
            pass
    return Response({'ok': True})


# File denoising endpoints
from .models import UploadedAudioFile
from django.core.files.base import ContentFile
from django.utils import timezone
import threading


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_audio_file(request):
    """Upload an audio file for denoising."""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)
    
    uploaded_file = request.FILES['file']
    
    # Validate file type
    allowed_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    filename = uploaded_file.name.lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        return Response({'error': 'Invalid file type. Allowed: WAV, MP3, FLAC, OGG, M4A'}, status=400)
    
    # Create database entry
    audio_file = UploadedAudioFile.objects.create(
        owner=request.user,
        original_filename=uploaded_file.name,
        original_file=uploaded_file,
        status='pending'
    )
    
    # Start denoising in background thread
    thread = threading.Thread(target=process_audio_file, args=(audio_file.id,))
    thread.daemon = True
    thread.start()
    
    return Response({
        'id': audio_file.id,
        'filename': audio_file.original_filename,
        'status': audio_file.status,
        'uploaded_at': audio_file.uploaded_at.isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_uploaded_files(request):
    """Get list of uploaded files for the current user."""
    files = UploadedAudioFile.objects.filter(owner=request.user)
    
    data = []
    for f in files:
        data.append({
            'id': f.id,
            'original_filename': f.original_filename,
            'original_file_url': f.original_file.url if f.original_file else None,
            'denoised_file_url': f.denoised_file.url if f.denoised_file else None,
            'status': f.status,
            'error_message': f.error_message,
            'duration': f.duration,
            'uploaded_at': f.uploaded_at.isoformat(),
            'processed_at': f.processed_at.isoformat() if f.processed_at else None,
        })
    
    return Response({'files': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_file_status(request, file_id):
    """Get the processing status of a specific file."""
    try:
        audio_file = UploadedAudioFile.objects.get(id=file_id, owner=request.user)
    except UploadedAudioFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=404)
    
    return Response({
        'id': audio_file.id,
        'status': audio_file.status,
        'denoised_file_url': audio_file.denoised_file.url if audio_file.denoised_file else None,
        'error_message': audio_file.error_message,
        'processed_at': audio_file.processed_at.isoformat() if audio_file.processed_at else None,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_uploaded_file(request, file_id):
    """Delete an uploaded file and its associated files from storage."""
    import os
    
    try:
        audio_file = UploadedAudioFile.objects.get(id=file_id, owner=request.user)
    except UploadedAudioFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=404)
    
    # Delete physical files from storage
    try:
        if audio_file.original_file:
            if audio_file.original_file.storage.exists(audio_file.original_file.name):
                audio_file.original_file.delete(save=False)
    except Exception as e:
        print(f"Error deleting original file: {e}")
    
    try:
        if audio_file.denoised_file:
            if audio_file.denoised_file.storage.exists(audio_file.denoised_file.name):
                audio_file.denoised_file.delete(save=False)
    except Exception as e:
        print(f"Error deleting denoised file: {e}")
    
    # Delete database record
    audio_file.delete()
    
    return Response({'message': 'File deleted successfully'}, status=200)


def process_audio_file(file_id):
    """Background task to denoise an audio file."""
    import os
    import tempfile
    from pathlib import Path
    import soundfile as sf
    import numpy as np
    from django.core.files import File
    
    try:
        audio_file = UploadedAudioFile.objects.get(id=file_id)
        audio_file.status = 'processing'
        audio_file.save()
        
        # Download original file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_input:
            temp_input_path = temp_input.name
            for chunk in audio_file.original_file.chunks():
                temp_input.write(chunk)
        
        # Convert to WAV if needed (using soundfile)
        try:
            data, sr = sf.read(temp_input_path)
        except Exception:
            # If soundfile can't read it, try using pydub for format conversion
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(temp_input_path)
                temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                audio.export(temp_wav.name, format='wav')
                temp_input_path = temp_wav.name
                data, sr = sf.read(temp_input_path)
            except Exception as e:
                raise Exception(f"Failed to read audio file: {e}")
        
        # Ensure mono
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        
        # Calculate duration
        duration = len(data) / sr
        audio_file.duration = duration
        audio_file.save()
        
        # Save as temporary WAV for denoising
        temp_wav_input = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        sf.write(temp_wav_input.name, data, sr)
        temp_wav_input.close()
        
        # Denoise using dfn2.py
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='_denoised.wav')
        temp_output.close()
        
        # Import and use dfn2 denoise function
        import dfn2
        dfn2.denoise_file(temp_wav_input.name, temp_output.name)
        
        # Save denoised file to model
        denoised_filename = f"denoised_{audio_file.original_filename}"
        if not denoised_filename.lower().endswith('.wav'):
            denoised_filename = os.path.splitext(denoised_filename)[0] + '.wav'
        
        with open(temp_output.name, 'rb') as f:
            audio_file.denoised_file.save(denoised_filename, File(f), save=False)
        
        audio_file.status = 'completed'
        audio_file.processed_at = timezone.now()
        audio_file.save()
        
        # Cleanup temp files
        try:
            os.unlink(temp_input_path)
            os.unlink(temp_wav_input.name)
            os.unlink(temp_output.name)
        except Exception:
            pass
            
    except Exception as e:
        print(f"Error processing audio file {file_id}: {e}")
        try:
            audio_file = UploadedAudioFile.objects.get(id=file_id)
            audio_file.status = 'failed'
            audio_file.error_message = str(e)
            audio_file.save()
        except Exception:
            pass
