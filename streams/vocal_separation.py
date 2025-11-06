"""
Vocal Separation views and processing using Demucs.
"""
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import VocalSeparationFile
from django.core.files.base import ContentFile
import threading
import os
import tempfile
from pathlib import Path


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_vocal_file(request):
    """Upload an audio file for vocal separation."""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)
    
    uploaded_file = request.FILES['file']
    
    # Validate file type
    allowed_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    filename = uploaded_file.name.lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        return Response({'error': 'Invalid file type. Allowed: WAV, MP3, FLAC, OGG, M4A'}, status=400)
    
    # Create database entry
    vocal_file = VocalSeparationFile.objects.create(
        owner=request.user,
        original_filename=uploaded_file.name,
        original_file=uploaded_file,
        status='pending'
    )
    
    # Start vocal separation in background thread
    thread = threading.Thread(target=process_vocal_separation, args=(vocal_file.id,))
    thread.daemon = True
    thread.start()
    
    return Response({
        'id': vocal_file.id,
        'filename': vocal_file.original_filename,
        'status': vocal_file.status,
        'uploaded_at': vocal_file.uploaded_at.isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_vocal_files(request):
    """Get list of vocal separation files for the current user."""
    files = VocalSeparationFile.objects.filter(owner=request.user)
    
    data = []
    for f in files:
        data.append({
            'id': f.id,
            'original_filename': f.original_filename,
            'original_file_url': f.original_file.url if f.original_file else None,
            'vocals_url': f.vocals_file.url if f.vocals_file else None,
            'instrumental_url': f.instrumental_file.url if f.instrumental_file else None,
            'status': f.status,
            'error_message': f.error_message,
            'uploaded_at': f.uploaded_at.isoformat(),
            'processed_at': f.processed_at.isoformat() if f.processed_at else None,
        })
    
    return Response({'files': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_vocal_file_status(request, file_id):
    """Get the processing status of a specific vocal separation file."""
    try:
        vocal_file = VocalSeparationFile.objects.get(id=file_id, owner=request.user)
    except VocalSeparationFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=404)
    
    return Response({
        'id': vocal_file.id,
        'status': vocal_file.status,
        'vocals_url': vocal_file.vocals_file.url if vocal_file.vocals_file else None,
        'instrumental_url': vocal_file.instrumental_file.url if vocal_file.instrumental_file else None,
        'error_message': vocal_file.error_message,
        'processed_at': vocal_file.processed_at.isoformat() if vocal_file.processed_at else None,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_vocal_file(request, file_id):
    """Delete a vocal separation file and its associated files from storage."""
    try:
        vocal_file = VocalSeparationFile.objects.get(id=file_id, owner=request.user)
    except VocalSeparationFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=404)
    
    # Delete physical files from storage
    try:
        if vocal_file.original_file:
            if vocal_file.original_file.storage.exists(vocal_file.original_file.name):
                vocal_file.original_file.delete(save=False)
    except Exception as e:
        print(f"Error deleting original file: {e}")
    
    try:
        if vocal_file.vocals_file:
            if vocal_file.vocals_file.storage.exists(vocal_file.vocals_file.name):
                vocal_file.vocals_file.delete(save=False)
    except Exception as e:
        print(f"Error deleting vocals file: {e}")
    
    try:
        if vocal_file.instrumental_file:
            if vocal_file.instrumental_file.storage.exists(vocal_file.instrumental_file.name):
                vocal_file.instrumental_file.delete(save=False)
    except Exception as e:
        print(f"Error deleting instrumental file: {e}")
    
    # Delete database record
    vocal_file.delete()
    
    return Response({'message': 'File deleted successfully'}, status=200)


def process_vocal_separation(file_id):
    """Background task to perform vocal separation using Demucs."""
    import shutil
    from django.core.files import File
    
    try:
        vocal_file = VocalSeparationFile.objects.get(id=file_id)
        vocal_file.status = 'processing'
        vocal_file.save()
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        
        # Save original file to temp location
        temp_input = os.path.join(temp_dir, vocal_file.original_filename)
        with open(temp_input, 'wb') as f:
            for chunk in vocal_file.original_file.chunks():
                f.write(chunk)
        
        # Create output directory
        output_dir = os.path.join(temp_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Run Demucs separation
        from demucs.separate import main as demucs_main
        
        model_name = "htdemucs"  # Using htdemucs model
        
        # Run Demucs with similar parameters as in demucs_separator.py
        demucs_args = [
            "--mp3",                  # Output as MP3
            "--two-stems", "vocals",  # Separate vocals and instrumental
            "-n", model_name,         # Model name
            "--out", output_dir,      # Output directory
            "--shifts", "5",          # Reduced shifts for faster processing
            "--overlap", "0.25",      # Default overlap
            temp_input                # Input file
        ]
        
        print(f"[Vocal Separation] Starting Demucs for file {file_id}...")
        demucs_main(demucs_args)
        print(f"[Vocal Separation] Demucs completed for file {file_id}")
        
        # Find the output files
        # Demucs creates: output_dir / model_name / filename / vocals.mp3 and no_vocals.mp3
        base_filename = Path(vocal_file.original_filename).stem
        vocals_path = os.path.join(output_dir, model_name, base_filename, "vocals.mp3")
        instrumental_path = os.path.join(output_dir, model_name, base_filename, "no_vocals.mp3")
        
        # Check if files exist
        if not os.path.exists(vocals_path):
            raise Exception(f"Vocals file not found at {vocals_path}")
        if not os.path.exists(instrumental_path):
            raise Exception(f"Instrumental file not found at {instrumental_path}")
        
        # Save vocals file
        vocals_filename = f"vocals_{base_filename}.mp3"
        with open(vocals_path, 'rb') as f:
            vocal_file.vocals_file.save(vocals_filename, File(f), save=False)
        
        # Save instrumental file
        instrumental_filename = f"instrumental_{base_filename}.mp3"
        with open(instrumental_path, 'rb') as f:
            vocal_file.instrumental_file.save(instrumental_filename, File(f), save=False)
        
        vocal_file.status = 'completed'
        vocal_file.processed_at = timezone.now()
        vocal_file.save()
        
        print(f"[Vocal Separation] Successfully completed processing for file {file_id}")
        
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp directory: {e}")
            
    except Exception as e:
        print(f"Error processing vocal separation file {file_id}: {e}")
        import traceback
        traceback.print_exc()
        try:
            vocal_file = VocalSeparationFile.objects.get(id=file_id)
            vocal_file.status = 'error'
            vocal_file.error_message = str(e)
            vocal_file.save()
        except Exception:
            pass
        finally:
            # Try to cleanup temp directory even on error
            try:
                if 'temp_dir' in locals():
                    shutil.rmtree(temp_dir)
            except Exception:
                pass
