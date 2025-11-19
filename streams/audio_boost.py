"""Audio volume boosting using FFmpeg volume filter."""
import os
import threading
import subprocess
import tempfile
from pathlib import Path
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.files.base import ContentFile
from .models import AudioBoostFile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_boost_file(request):
    """Upload an audio file for volume boost."""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    boost_level = request.data.get('boost_level', '3x')
    
    # Validate boost level
    if boost_level not in ['2x', '3x', '4x', '5x']:
        boost_level = '3x'
    
    # Validate file type
    allowed_extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac']
    file_ext = os.path.splitext(file.name)[1].lower()
    if file_ext not in allowed_extensions:
        return Response({'error': 'Invalid file type'}, status=400)
    
    # Create database entry
    audio_file = AudioBoostFile.objects.create(
        owner=request.user,
        original_filename=file.name,
        original_file=file,
        boost_level=boost_level,
        status='pending'
    )
    
    # Start background processing
    thread = threading.Thread(target=process_audio_boost, args=(audio_file.id,))
    thread.start()
    
    return Response({
        'id': audio_file.id,
        'filename': audio_file.original_filename,
        'boost_level': boost_level,
        'status': 'pending',
        'message': 'File uploaded successfully. Processing started.'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_boost_files(request):
    """Get list of audio boost files for the current user."""
    files = AudioBoostFile.objects.filter(owner=request.user)
    
    data = []
    for f in files:
        data.append({
            'id': f.id,
            'original_filename': f.original_filename,
            'original_file_url': f.original_file.url if f.original_file else None,
            'boosted_file_url': f.boosted_file.url if f.boosted_file else None,
            'boost_level': f.boost_level,
            'status': f.status,
            'error_message': f.error_message,
            'uploaded_at': f.uploaded_at.isoformat(),
            'processed_at': f.processed_at.isoformat() if f.processed_at else None,
        })
    
    return Response({'files': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_boost_file_status(request, file_id):
    """Get the processing status of a specific boost file."""
    try:
        audio_file = AudioBoostFile.objects.get(id=file_id, owner=request.user)
    except AudioBoostFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=404)
    
    return Response({
        'id': audio_file.id,
        'status': audio_file.status,
        'boosted_file_url': audio_file.boosted_file.url if audio_file.boosted_file else None,
        'error_message': audio_file.error_message,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_boost_file(request, file_id):
    """Delete an audio boost file."""
    try:
        audio_file = AudioBoostFile.objects.get(id=file_id, owner=request.user)
    except AudioBoostFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=404)
    
    # Delete files from storage
    try:
        if audio_file.original_file:
            if audio_file.original_file.storage.exists(audio_file.original_file.name):
                audio_file.original_file.delete(save=False)
        
        if audio_file.boosted_file:
            if audio_file.boosted_file.storage.exists(audio_file.boosted_file.name):
                audio_file.boosted_file.delete(save=False)
    except Exception as e:
        print(f"Error deleting boost files: {e}")
    
    audio_file.delete()
    return Response({'message': 'File deleted successfully'})


def process_audio_boost(file_id):
    """Background task to boost audio volume using FFmpeg volume filter."""
    try:
        audio_file = AudioBoostFile.objects.get(id=file_id)
        audio_file.status = 'processing'
        audio_file.save()
        
        # Get input file path
        input_path = audio_file.original_file.path
        
        # Create output directory
        output_dir = os.path.join(os.path.dirname(input_path), '..', 'boosted')
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename (MP3 for compression)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_filename = f"{base_name}_boosted.mp3"
        output_path = os.path.join(output_dir, output_filename)
        
        # Volume multipliers based on boost level
        volume_multipliers = {
            '2x': 2.0,   # 2x volume
            '3x': 3.0,   # 3x volume
            '4x': 4.0,   # 4x volume
            '5x': 5.0,   # 5x volume
        }
        
        multiplier = volume_multipliers.get(audio_file.boost_level, 3.0)
        
        print(f"[Audio Boost] Boosting volume by {multiplier}x and converting to MP3...")
        
        # Apply volume boost and convert to MP3 using FFmpeg
        boost_cmd = [
            'ffmpeg',
            '-i', input_path,
            '-af', f'volume={multiplier}',
            '-b:a', '192k',  # 192 kbps MP3 bitrate
            '-ar', '48000',  # Standard sample rate
            '-y',
            output_path
        ]
        
        subprocess.run(
            boost_cmd,
            check=True,
            capture_output=True,
            timeout=300
        )
        
        # Save boosted file to model
        print(f"[Audio Boost] Saving boosted MP3 to database...")
        with open(output_path, 'rb') as f:
            audio_file.boosted_file.save(
                output_filename,
                ContentFile(f.read()),
                save=True
            )
        
        # Mark as completed
        audio_file.status = 'completed'
        audio_file.processed_at = timezone.now()
        audio_file.save()
        
        print(f"[Audio Boost] ✓ Processing completed - Status: {audio_file.status}")
        print(f"  Output file: {audio_file.boosted_file.name}")
        
        # Clean up temporary file
        if os.path.exists(output_path):
            os.remove(output_path)
        
        print(f"Audio boost completed for file {file_id}")
        
    except AudioBoostFile.DoesNotExist:
        print(f"AudioBoostFile {file_id} not found")
    except subprocess.TimeoutExpired:
        print(f"Audio boost timed out for file {file_id}")
        try:
            audio_file = AudioBoostFile.objects.get(id=file_id)
            audio_file.status = 'error'
            audio_file.error_message = "Processing timed out (file too large or corrupted)"
            audio_file.save()
        except:
            pass
    except Exception as e:
        print(f"Error processing audio boost for file {file_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            audio_file = AudioBoostFile.objects.get(id=file_id)
            audio_file.status = 'error'
            audio_file.error_message = str(e)
            audio_file.save()
        except:
            pass
