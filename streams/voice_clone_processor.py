"""
Voice cloning/conversion processor using external Voice Clone API service.
This module calls a dedicated voice cloning microservice running on port 8001.
"""
import os
import tempfile
import requests
import subprocess
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import VoiceCloneFile

# Voice Clone API Configuration
VOICE_CLONE_API_URL = "http://localhost:8001/api/clone/"
VOICE_CLONE_API_TIMEOUT = 300  # 5 minutes timeout for processing


def process_voice_clone(file_id):
    """
    Process voice cloning for a given file ID using external Voice Clone API service.
    """
    try:
        clone_file = VoiceCloneFile.objects.get(id=file_id)
        clone_file.status = 'processing'
        clone_file.save()
        
        print(f"[Voice Clone] Processing file ID {file_id}")
        print(f"[Voice Clone] Source: {clone_file.source_filename}")
        print(f"[Voice Clone] Target voice: {clone_file.target_voice_filename}")
        
        source_path = clone_file.source_file.path
        target_voice_path = clone_file.target_voice_file.path
        
        # Call external voice clone API
        print(f"[Voice Clone] Calling external API at {VOICE_CLONE_API_URL}")
        output_path = call_voice_clone_api(source_path, target_voice_path)
        
        if not output_path:
            raise Exception("Voice clone API returned no output")
        
        # Convert to MP3
        output_filename = f"cloned_{clone_file.source_filename}"
        if not output_filename.endswith('.mp3'):
            output_filename = output_filename.rsplit('.', 1)[0] + '.mp3'
        
        temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_mp3.close()
        
        subprocess.run([
            'ffmpeg', '-i', output_path,
            '-codec:a', 'libmp3lame',
            '-b:a', '192k',
            '-y', temp_mp3.name
        ], check=True, capture_output=True)
        
        # Save to model
        with open(temp_mp3.name, 'rb') as f:
            clone_file.converted_file.save(
                output_filename,
                ContentFile(f.read()),
                save=True
            )
        
        # Cleanup
        if os.path.exists(output_path):
            os.unlink(output_path)
        os.unlink(temp_mp3.name)
        
        clone_file.status = 'completed'
        clone_file.processed_at = timezone.now()
        clone_file.save()
        
        print(f"[Voice Clone] Completed: {output_filename}")
        
    except VoiceCloneFile.DoesNotExist:
        print(f"[Voice Clone] File ID {file_id} not found")
    except Exception as e:
        print(f"[Voice Clone] Error processing file ID {file_id}: {e}")
        import traceback
        traceback.print_exc()
        try:
            clone_file = VoiceCloneFile.objects.get(id=file_id)
            clone_file.status = 'failed'
            clone_file.error_message = str(e)
            clone_file.save()
        except:
            pass


def call_voice_clone_api(source_audio_path, target_audio_path, 
                         diffusion_steps=100, f0_condition=True, 
                         auto_f0_adjust=True, inference_cfg_rate=0.7):
    """
    Call the external voice cloning microservice API.
    
    Args:
        source_audio_path: Path to source audio file (content to transfer)
        target_audio_path: Path to target audio file (voice style to clone)
        diffusion_steps: Number of diffusion steps (default: 100)
        f0_condition: Use F0 conditioning (default: True)
        auto_f0_adjust: Auto adjust F0 (default: True)
        inference_cfg_rate: Inference CFG rate (default: 0.7)
    
    Returns:
        Path to the output audio file, or None if failed
    """
    try:
        print(f"[Voice Clone API] Opening source: {source_audio_path}")
        print(f"[Voice Clone API] Opening target: {target_audio_path}")
        
        with open(source_audio_path, 'rb') as source_file, \
             open(target_audio_path, 'rb') as target_file:
            
            files = {
                'source_audio': source_file,
                'target_audio': target_file,
            }
            
            data = {
                'diffusion_steps': diffusion_steps,
                'f0_condition': 'true' if f0_condition else 'false',
                'auto_f0_adjust': 'true' if auto_f0_adjust else 'false',
                'inference_cfg_rate': inference_cfg_rate
            }
            
            print(f"[Voice Clone API] Sending request to {VOICE_CLONE_API_URL}")
            print(f"[Voice Clone API] Parameters: {data}")
            
            response = requests.post(
                VOICE_CLONE_API_URL, 
                files=files, 
                data=data, 
                timeout=VOICE_CLONE_API_TIMEOUT
            )
            
            if response.status_code == 200:
                # Save the response audio to a temporary file
                output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
                
                with open(output_path, 'wb') as output_file:
                    output_file.write(response.content)
                
                print(f"[Voice Clone API] Success! Saved to {output_path}")
                return output_path
            else:
                error_msg = f"API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data}"
                except:
                    error_msg += f": {response.text[:200]}"
                
                print(f"[Voice Clone API] Error: {error_msg}")
                return None
                
    except requests.exceptions.Timeout:
        print(f"[Voice Clone API] Timeout after {VOICE_CLONE_API_TIMEOUT} seconds")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[Voice Clone API] Connection error - is the service running on port 8001?")
        return None
    except Exception as e:
        print(f"[Voice Clone API] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None

