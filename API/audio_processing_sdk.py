"""
Audio Processing Services - Python SDK
A simple Python client for interacting with the Audio Processing Services API.
"""

import requests
import time
from typing import Optional, Dict, List
from pathlib import Path
import importlib
from unittest import result
import os


class AudioProcessingClient:
    """
    Client for Audio Processing Services API
    
    Example:
        client = AudioProcessingClient("http://localhost:8000")
        client.login("username", "password")
        
        # Denoise a file
        result = client.denoise_file("audio.mp3", boost_level="2x")
        file_id = result['file_id']
        
        # Wait for completion
        processed = client.wait_for_denoise(file_id)
        print(f"Download: {processed['denoised_url']}")
    """
    
    def __init__(self, base_url: str):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the API (e.g., http://localhost:8000)
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.csrf_token = None
    
    def login(self, username: str, password: str) -> bool:
        """
        Login to get session credentials.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if login successful, False otherwise
        """
        url = f"{self.base_url}/login/"
        
        # Get CSRF token
        response = self.session.get(url)
        if 'csrftoken' in self.session.cookies:
            self.csrf_token = self.session.cookies['csrftoken']
        
        # Login
        data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': self.csrf_token
        }
        response = self.session.post(url, data=data)
        
        # Update CSRF token after login (Django rotates CSRF tokens)
        if 'csrftoken' in self.session.cookies:
            self.csrf_token = self.session.cookies['csrftoken']
        
        return response.status_code == 200 or response.url.endswith('/')
    
    def _get_csrf_header(self) -> Dict[str, str]:
        """Get CSRF header for POST requests."""
        if self.csrf_token:
            return {'X-CSRFToken': self.csrf_token}
        return {}
    
    # ==================== FILE DENOISE ====================
    
    def denoise_file(self, file_path: str, boost_level: str = 'none') -> Dict:
        """
        Upload audio file for denoising.
        
        Args:
            file_path: Path to audio file
            boost_level: Volume boost ('none', '2x', '3x', '4x', '5x')
            
        Returns:
            Response dict with file_id
        """
        url = f"{self.base_url}/api/denoise/upload/"
        files = {'file': open(file_path, 'rb')}
        data = {'boost_level': boost_level}
        
        response = self.session.post(url, files=files, data=data, headers=self._get_csrf_header())
        return response.json()
    
    def list_denoised_files(self) -> List[Dict]:
        """Get list of all denoised files."""
        url = f"{self.base_url}/api/denoise/files/"
        response = self.session.get(url)
        return response.json().get('files', [])
    
    def get_denoise_status(self, file_id: int) -> Dict:
        """Get processing status of denoised file."""
        url = f"{self.base_url}/api/denoise/files/{file_id}/status/"
        response = self.session.get(url)
        return response.json()
    
    def delete_denoised_file(self, file_id: int) -> Dict:
        """Delete denoised file."""
        url = f"{self.base_url}/api/denoise/files/{file_id}/delete/"
        response = self.session.delete(url, headers=self._get_csrf_header())
        return response.json()
    
    def wait_for_denoise(self, file_id: int, check_interval: int = 5, timeout: int = 600) -> Optional[Dict]:
        """
        Wait for denoising to complete.
        
        Args:
            file_id: ID of the file
            check_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            
        Returns:
            File data when completed, None if failed or timeout
        """
        elapsed = 0
        while elapsed < timeout:
            data = self.get_denoise_status(file_id)
            
            if data['status'] == 'completed':
                return data
            elif data['status'] == 'failed':
                print(f"Processing failed: {data.get('error_message')}")
                return None
            
            print(f"Status: {data['status']}... waiting {check_interval}s")
            time.sleep(check_interval)
            elapsed += check_interval
        
        print("Timeout waiting for processing")
        return None
    
    # ==================== VOCAL SEPARATION ====================
    
    def separate_vocals(self, file_path: str) -> Dict:
        """
        Upload audio file for vocal separation.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Response dict with file_id
        """
        url = f"{self.base_url}/api/vocal/separate/"
        files = {'file': open(file_path, 'rb')}
        
        response = self.session.post(url, files=files, headers=self._get_csrf_header())
        return response.json()
    
    def list_vocal_files(self) -> List[Dict]:
        """Get list of all vocal separation files."""
        url = f"{self.base_url}/api/vocal/files/"
        response = self.session.get(url)
        return response.json().get('files', [])
    
    def get_vocal_status(self, file_id: int) -> Dict:
        """Get processing status of vocal separation."""
        url = f"{self.base_url}/api/vocal/files/{file_id}/status/"
        response = self.session.get(url)
        return response.json()
    
    def delete_vocal_file(self, file_id: int) -> Dict:
        """Delete vocal separation file."""
        url = f"{self.base_url}/api/vocal/files/{file_id}/delete/"
        response = self.session.delete(url, headers=self._get_csrf_header())
        return response.json()
    
    def wait_for_vocal_separation(self, file_id: int, check_interval: int = 5, timeout: int = 900) -> Optional[Dict]:
        """Wait for vocal separation to complete."""
        elapsed = 0
        while elapsed < timeout:
            data = self.get_vocal_status(file_id)
            
            if data['status'] == 'completed':
                return data
            elif data['status'] == 'error':
                print(f"Processing failed: {data.get('error_message')}")
                return None
            
            print(f"Status: {data['status']}... waiting {check_interval}s")
            time.sleep(check_interval)
            elapsed += check_interval
        
        return None
    
    # ==================== AUDIO BOOST ====================
    
    def boost_audio(self, file_path: str, boost_level: str = '3x') -> Dict:
        """
        Upload audio file for volume boost.
        
        Args:
            file_path: Path to audio file
            boost_level: Boost intensity ('2x', '3x', '4x', '5x')
            
        Returns:
            Response dict with file_id
        """
        url = f"{self.base_url}/api/boost/upload/"
        files = {'file': open(file_path, 'rb')}
        data = {'boost_level': boost_level}
        
        response = self.session.post(url, files=files, data=data, headers=self._get_csrf_header())
        return response.json()
    
    def list_boost_files(self) -> List[Dict]:
        """Get list of all audio boost files."""
        url = f"{self.base_url}/api/boost/files/"
        response = self.session.get(url)
        return response.json().get('files', [])
    
    def get_boost_status(self, file_id: int) -> Dict:
        """Get processing status of audio boost."""
        url = f"{self.base_url}/api/boost/files/{file_id}/status/"
        response = self.session.get(url)
        return response.json()
    
    def delete_boost_file(self, file_id: int) -> Dict:
        """Delete audio boost file."""
        url = f"{self.base_url}/api/boost/files/{file_id}/delete/"
        response = self.session.delete(url, headers=self._get_csrf_header())
        return response.json()
    
    def wait_for_boost(self, file_id: int, check_interval: int = 3, timeout: int = 300) -> Optional[Dict]:
        """Wait for audio boost to complete."""
        elapsed = 0
        while elapsed < timeout:
            data = self.get_boost_status(file_id)
            
            if data['status'] == 'completed':
                return data
            elif data['status'] == 'error':
                print(f"Processing failed: {data.get('error_message')}")
                return None
            
            print(f"Status: {data['status']}... waiting {check_interval}s")
            time.sleep(check_interval)
            elapsed += check_interval
        
        return None
    
    # ==================== SPEAKER EXTRACTION ====================
    
    def extract_speaker(self, conversation_file: str, target_speaker_file: str, boost_level: str = 'none') -> Dict:
        """
        Extract target speaker from conversation.
        
        Args:
            conversation_file: Path to conversation audio
            target_speaker_file: Path to target speaker sample
            boost_level: Volume boost ('none', '2x', '3x', '4x', '5x')
            
        Returns:
            Response dict with file_id
        """
        url = f"{self.base_url}/api/speaker/extract/"
        files = {
            'conversation_file': open(conversation_file, 'rb'),
            'target_file': open(target_speaker_file, 'rb')
        }
        data = {'boost_level': boost_level}
        
        response = self.session.post(url, files=files, data=data, headers=self._get_csrf_header())
        return response.json()
    
    def list_speaker_files(self) -> List[Dict]:
        """Get list of all speaker extraction files."""
        url = f"{self.base_url}/api/speaker/files/"
        response = self.session.get(url)
        return response.json().get('files', [])
    
    def delete_speaker_file(self, file_id: int) -> Dict:
        """Delete speaker extraction file."""
        url = f"{self.base_url}/api/speaker/files/{file_id}/delete/"
        response = self.session.delete(url, headers=self._get_csrf_header())
        return response.json()
    
    # Note: Speaker extraction doesn't have a status endpoint, use list to check
    def wait_for_speaker_extraction(self, file_id: int, check_interval: int = 10, timeout: int = 1200) -> Optional[Dict]:
        """Wait for speaker extraction to complete by polling the file list."""
        elapsed = 0
        while elapsed < timeout:
            files = self.list_speaker_files()
            file_data = next((f for f in files if f['id'] == file_id), None)
            
            if not file_data:
                print("File not found")
                return None
            
            if file_data['status'] == 'completed':
                return file_data
            elif file_data['status'] == 'error':
                print(f"Processing failed: {file_data.get('error_message')}")
                return None
            
            print(f"Status: {file_data['status']}... waiting {check_interval}s")
            time.sleep(check_interval)
            elapsed += check_interval
        
        return None
    
    # ==================== UTILITY METHODS ====================
    
    def download_file(self, url: str, save_path: str):
        """
        Download processed file.
        
        Args:
            url: URL of the file (from response)
            save_path: Local path to save file
        """
        if not url.startswith('http'):
            url = f"{self.base_url}{url}"
        
        response = self.session.get(url, stream=True)
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Downloaded to: {save_path}")


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Initialize client
    client = AudioProcessingClient("http://localhost:8000")
    
    # Login
    if not client.login("your_username", "your_password"):
        print("Login failed!")
        exit(1)
    
    print("Login successful!")
    
    # Example 1: Denoise a file
    print("\n=== Denoising File ===")
    result = client.denoise_file("my_audio.mp3", boost_level="2x")
    print(f"Upload result: {result}")
    
    if result.get('status') == 'success':
        file_id = result['file_id']
        processed = client.wait_for_denoise(file_id)
        
        if processed:
            print(f"Denoised file URL: {processed['denoised_url']}")
            client.download_file(processed['denoised_url'], "denoised_audio.mp3")
    
    # Example 2: Separate vocals
    print("\n=== Separating Vocals ===")
    result = client.separate_vocals("song.mp3")
    
    if result.get('status') == 'success':
        file_id = result['file_id']
        processed = client.wait_for_vocal_separation(file_id)
        
        if processed:
            print(f"Vocals: {processed['vocals_url']}")
            print(f"Instrumental: {processed['instrumental_url']}")
            client.download_file(processed['vocals_url'], "vocals.mp3")
            client.download_file(processed['instrumental_url'], "instrumental.mp3")
    
    # Example 3: Boost audio
    print("\n=== Boosting Audio ===")
    result = client.boost_audio("quiet_audio.mp3", boost_level="4x")
    
    if result.get('status') == 'success':
        file_id = result['file_id']
        processed = client.wait_for_boost(file_id)
        
        if processed:
            print(f"Boosted file URL: {processed['boosted_url']}")
            client.download_file(processed['boosted_url'], "boosted_audio.mp3")
    
    # Example 4: Extract speaker
    print("\n=== Extracting Speaker ===")
    result = client.extract_speaker("meeting.mp3", "speaker_sample.mp3", boost_level="2x")
    
    if result.get('status') == 'success':
        file_id = result['file_id']
        processed = client.wait_for_speaker_extraction(file_id)
        
        if processed:
            print(f"Similarity: {processed['similarity_score']}%")
            print(f"Extracted file URL: {processed['extracted_url']}")
            client.download_file(processed['extracted_url'], "extracted_speaker.mp3")
    
    # List all files
    print("\n=== All Denoised Files ===")
    files = client.list_denoised_files()
    for file in files:
        print(f"- {file['filename']} ({file['status']})")



# ========== Functions ===============================================

def login_rtdenoise(BASE_URL, USERNAME, PASSWORD):
    client = AudioProcessingClient(BASE_URL)
    client.login(USERNAME, PASSWORD)
    print("Logged in")
    return client


def denoise_file(client, audio_file, output_file, boost_level):
    result = client.denoise_file(audio_file, boost_level=boost_level)
    if result.get('status') == 'pending':
        print(f"✓ Uploaded: {result['filename']} (ID: {result['id']})")
        
        # Wait for processing to complete
        processed = client.wait_for_denoise(result['id'])
        if processed:
            print(f"✓ Processing completed!")
            print(f"  Status: {processed['status']}")
            print(f"  File URL: {processed['denoised_file_url']}")
            
            # Download the result
            client.download_file(processed['denoised_file_url'], output_file)
            print(f"✓ Downloaded to: {output_file}")



def separate_vocals(client, audio_file, output_vocals, output_instrumental):
    result = client.separate_vocals(audio_file)
    if result.get('status') == 'pending':
        print(f"✓ Uploaded: {result['filename']} (ID: {result['id']})")
        
        # Wait for processing (takes 2-5 minutes)
        processed = client.wait_for_vocal_separation(result['id'])
        if processed:
            print(f"✓ Vocal separation completed!")
            print(f"  Vocals: {processed['vocals_url']}")
            print(f"  Instrumental: {processed['instrumental_url']}")
            
            # Download both files
            client.download_file(processed['vocals_url'], output_vocals)
            client.download_file(processed['instrumental_url'], output_instrumental)
            print(f"✓ Downloaded vocals and instrumental!")


def extract_speaker(client, conversation_file, target_speaker_file, output_file, boost_level):
    result = client.extract_speaker(conversation_file, target_speaker_file, boost_level=boost_level)
    if result.get('status') == 'pending':
        print(f"✓ Uploaded files (ID: {result['id']})")
        
        # Wait for processing (takes 5-15 minutes)
        processed = client.wait_for_speaker_extraction(result['id'])
        if processed:
            print(f"✓ Speaker extraction completed!")
            print(f"  Similarity: {processed['similarity_score']}%")
            print(f"  Extracted file: {processed['extracted_url']}")
            
            # Download the result
            client.download_file(processed['extracted_url'], output_file)
            print(f"✓ Downloaded to: {output_file}")


def boost_audio(client, audio_file, output_file, boost_level):
    result = client.boost_audio(audio_file, boost_level=boost_level)
    if result.get('status') == 'pending':
        print(f"✓ Uploaded: {result['filename']} (ID: {result['id']})")
        
        # Wait for processing (usually ~30 seconds)
        processed = client.wait_for_boost(result['id'])
        if processed:
            print(f"✓ Audio boost completed!")
            print(f"  Boost level: {boost_level}")
            print(f"  File URL: {processed['boosted_file_url']}")
            
            # Download the result
            client.download_file(processed['boosted_file_url'], output_file)
            print(f"✓ Downloaded to: {output_file}")