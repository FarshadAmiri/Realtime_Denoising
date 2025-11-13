# Audio Processing Services - API Documentation

## Overview
This document provides comprehensive documentation for all RESTful APIs available in the Audio Processing Services platform. The platform offers four main audio processing services accessible through the "Denoise a file" modal.

## Base URL
```
http://your-domain.com
```

## Authentication
All API endpoints require authentication. Include the session cookie in requests or use Django's CSRF token for POST requests.

**Headers Required:**
```
Content-Type: multipart/form-data (for file uploads)
X-CSRFToken: <your-csrf-token>
Cookie: sessionid=<your-session-id>
```

---

## Table of Contents
1. [File Denoise Service](#1-file-denoise-service)
2. [Vocal Separation Service](#2-vocal-separation-service)
3. [Audio Boost Service](#3-audio-boost-service)
4. [Speaker Extraction Service](#4-speaker-extraction-service)

---

## 1. File Denoise Service

### 1.1 Upload Audio File for Denoising

**Endpoint:** `POST /api/denoise/upload/`

**Description:** Upload an audio file for noise reduction processing. Optionally apply volume boost after denoising.

**Request:**
- **Method:** POST
- **Content-Type:** multipart/form-data

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| audio_file | File | Yes | Audio file (MP3, WAV, M4A, FLAC) |
| boost_level | String | No | Volume boost level: 'none', '2x', '3x', '4x', '5x' (default: 'none') |

**Example Request (cURL):**
```bash
curl -X POST http://your-domain.com/api/denoise/upload/ \
  -H "X-CSRFToken: your-csrf-token" \
  -F "audio_file=@/path/to/audio.mp3" \
  -F "boost_level=2x" \
  -b "sessionid=your-session-id"
```

**Example Request (Python):**
```python
import requests

url = "http://your-domain.com/api/denoise/upload/"
files = {'audio_file': open('audio.mp3', 'rb')}
data = {'boost_level': '2x'}
headers = {'X-CSRFToken': 'your-csrf-token'}
cookies = {'sessionid': 'your-session-id'}

response = requests.post(url, files=files, data=data, headers=headers, cookies=cookies)
print(response.json())
```

**Example Request (JavaScript/Fetch):**
```javascript
const formData = new FormData();
formData.append('audio_file', fileInput.files[0]);
formData.append('boost_level', '2x');

fetch('/api/denoise/upload/', {
    method: 'POST',
    body: formData,
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    },
    credentials: 'same-origin'
})
.then(response => response.json())
.then(data => console.log(data));
```

**Success Response (200 OK):**
```json
{
    "status": "success",
    "message": "File uploaded successfully. Processing started.",
    "file_id": 123,
    "filename": "audio.mp3"
}
```

**Error Responses:**

*400 Bad Request:*
```json
{
    "status": "error",
    "message": "No audio file provided"
}
```

*415 Unsupported Media Type:*
```json
{
    "status": "error",
    "message": "Unsupported file type. Please upload MP3, WAV, M4A, or FLAC files."
}
```

---

### 1.2 List Denoised Files

**Endpoint:** `GET /api/denoise/files/`

**Description:** Retrieve a list of all uploaded files for the authenticated user, including their processing status.

**Request:**
- **Method:** GET
- **Parameters:** None

**Example Request (cURL):**
```bash
curl -X GET http://your-domain.com/api/denoise/files/ \
  -b "sessionid=your-session-id"
```

**Example Request (Python):**
```python
import requests

url = "http://your-domain.com/api/denoise/files/"
cookies = {'sessionid': 'your-session-id'}

response = requests.get(url, cookies=cookies)
print(response.json())
```

**Success Response (200 OK):**
```json
{
    "files": [
        {
            "id": 123,
            "filename": "audio.mp3",
            "status": "completed",
            "boost_level": "2x",
            "duration": "03:45",
            "original_url": "/media/uploads/original/audio.mp3",
            "denoised_url": "/media/uploads/denoised/audio_denoised.mp3",
            "uploaded_at": "2024-11-13T10:30:00Z",
            "processed_at": "2024-11-13T10:35:00Z"
        },
        {
            "id": 124,
            "filename": "song.wav",
            "status": "processing",
            "boost_level": "none",
            "duration": "04:12",
            "original_url": "/media/uploads/original/song.wav",
            "denoised_url": null,
            "uploaded_at": "2024-11-13T11:00:00Z",
            "processed_at": null
        }
    ]
}
```

**Status Values:**
- `pending`: File uploaded, waiting for processing
- `processing`: Currently being processed
- `completed`: Processing finished successfully
- `failed`: Processing failed (check error_message)

---

### 1.3 Get File Status

**Endpoint:** `GET /api/denoise/files/<file_id>/status/`

**Description:** Get the current processing status of a specific file.

**Request:**
- **Method:** GET
- **URL Parameters:** 
  - `file_id` (integer): ID of the uploaded file

**Example Request (cURL):**
```bash
curl -X GET http://your-domain.com/api/denoise/files/123/status/ \
  -b "sessionid=your-session-id"
```

**Success Response (200 OK):**
```json
{
    "id": 123,
    "filename": "audio.mp3",
    "status": "completed",
    "boost_level": "2x",
    "duration": "03:45",
    "original_url": "/media/uploads/original/audio.mp3",
    "denoised_url": "/media/uploads/denoised/audio_denoised.mp3",
    "error_message": null
}
```

**Error Response (404 Not Found):**
```json
{
    "status": "error",
    "message": "File not found"
}
```

---

### 1.4 Delete Denoised File

**Endpoint:** `DELETE /api/denoise/files/<file_id>/delete/`

**Description:** Delete an uploaded file and its processed version.

**Request:**
- **Method:** DELETE
- **URL Parameters:** 
  - `file_id` (integer): ID of the file to delete

**Example Request (cURL):**
```bash
curl -X DELETE http://your-domain.com/api/denoise/files/123/delete/ \
  -H "X-CSRFToken: your-csrf-token" \
  -b "sessionid=your-session-id"
```

**Example Request (JavaScript/Fetch):**
```javascript
fetch(`/api/denoise/files/${fileId}/delete/`, {
    method: 'DELETE',
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    },
    credentials: 'same-origin'
})
.then(response => response.json())
.then(data => console.log(data));
```

**Success Response (200 OK):**
```json
{
    "status": "success",
    "message": "File deleted successfully"
}
```

**Error Response (404 Not Found):**
```json
{
    "status": "error",
    "message": "File not found"
}
```

---

## 2. Vocal Separation Service

### 2.1 Upload File for Vocal Separation

**Endpoint:** `POST /api/vocal/separate/`

**Description:** Upload an audio file to separate vocals from instrumental using Demucs AI model.

**Request:**
- **Method:** POST
- **Content-Type:** multipart/form-data

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| audio_file | File | Yes | Audio file (MP3, WAV, M4A, FLAC) |

**Example Request (cURL):**
```bash
curl -X POST http://your-domain.com/api/vocal/separate/ \
  -H "X-CSRFToken: your-csrf-token" \
  -F "audio_file=@/path/to/song.mp3" \
  -b "sessionid=your-session-id"
```

**Example Request (Python):**
```python
import requests

url = "http://your-domain.com/api/vocal/separate/"
files = {'audio_file': open('song.mp3', 'rb')}
headers = {'X-CSRFToken': 'your-csrf-token'}
cookies = {'sessionid': 'your-session-id'}

response = requests.post(url, files=files, headers=headers, cookies=cookies)
print(response.json())
```

**Success Response (200 OK):**
```json
{
    "status": "success",
    "message": "Vocal separation started",
    "file_id": 456
}
```

**Error Response (400 Bad Request):**
```json
{
    "error": "No file provided"
}
```

---

### 2.2 List Vocal Separation Files

**Endpoint:** `GET /api/vocal/files/`

**Description:** Retrieve all vocal separation files for the authenticated user.

**Request:**
- **Method:** GET
- **Parameters:** None

**Example Request (cURL):**
```bash
curl -X GET http://your-domain.com/api/vocal/files/ \
  -b "sessionid=your-session-id"
```

**Success Response (200 OK):**
```json
{
    "files": [
        {
            "id": 456,
            "filename": "song.mp3",
            "status": "completed",
            "original_url": "/media/uploads/vocal_separation/original/song.mp3",
            "vocals_url": "/media/uploads/vocal_separation/vocals/song_vocals.mp3",
            "instrumental_url": "/media/uploads/vocal_separation/instrumental/song_instrumental.mp3",
            "uploaded_at": "2024-11-13T12:00:00Z",
            "processed_at": "2024-11-13T12:05:00Z",
            "error_message": null
        }
    ]
}
```

**Status Values:**
- `pending`: File uploaded, waiting for processing
- `processing`: Currently separating vocals
- `completed`: Separation finished successfully
- `error`: Processing failed

---

### 2.3 Get Vocal Separation Status

**Endpoint:** `GET /api/vocal/files/<file_id>/status/`

**Description:** Check the processing status of a specific vocal separation task.

**Request:**
- **Method:** GET
- **URL Parameters:** 
  - `file_id` (integer): ID of the vocal separation file

**Example Request (cURL):**
```bash
curl -X GET http://your-domain.com/api/vocal/files/456/status/ \
  -b "sessionid=your-session-id"
```

**Success Response (200 OK):**
```json
{
    "id": 456,
    "filename": "song.mp3",
    "status": "processing",
    "progress": 75,
    "original_url": "/media/uploads/vocal_separation/original/song.mp3",
    "vocals_url": null,
    "instrumental_url": null
}
```

---

### 2.4 Delete Vocal Separation File

**Endpoint:** `DELETE /api/vocal/files/<file_id>/delete/`

**Description:** Delete a vocal separation file and its outputs.

**Request:**
- **Method:** DELETE
- **URL Parameters:** 
  - `file_id` (integer): ID of the file to delete

**Example Request (cURL):**
```bash
curl -X DELETE http://your-domain.com/api/vocal/files/456/delete/ \
  -H "X-CSRFToken: your-csrf-token" \
  -b "sessionid=your-session-id"
```

**Success Response (200 OK):**
```json
{
    "status": "success"
}
```

---

## 3. Audio Boost Service

### 3.1 Upload File for Audio Boost

**Endpoint:** `POST /api/boost/upload/`

**Description:** Upload an audio file for volume boost/normalization.

**Request:**
- **Method:** POST
- **Content-Type:** multipart/form-data

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| audio_file | File | Yes | Audio file (MP3, WAV, M4A, FLAC) |
| boost_level | String | No | Boost intensity: '2x', '3x', '4x', '5x' (default: '3x') |

**Example Request (cURL):**
```bash
curl -X POST http://your-domain.com/api/boost/upload/ \
  -H "X-CSRFToken: your-csrf-token" \
  -F "audio_file=@/path/to/quiet_audio.mp3" \
  -F "boost_level=4x" \
  -b "sessionid=your-session-id"
```

**Example Request (Python):**
```python
import requests

url = "http://your-domain.com/api/boost/upload/"
files = {'audio_file': open('quiet_audio.mp3', 'rb')}
data = {'boost_level': '4x'}
headers = {'X-CSRFToken': 'your-csrf-token'}
cookies = {'sessionid': 'your-session-id'}

response = requests.post(url, files=files, data=data, headers=headers, cookies=cookies)
print(response.json())
```

**Success Response (200 OK):**
```json
{
    "status": "success",
    "message": "Audio boost started",
    "file_id": 789
}
```

**Boost Levels:**
- `2x`: 2x volume increase
- `3x`: 3x volume increase (recommended)
- `4x`: 4x volume increase
- `5x`: 5x volume increase (maximum)

**Error Response (400 Bad Request):**
```json
{
    "error": "No file provided"
}
```

---

### 3.2 List Audio Boost Files

**Endpoint:** `GET /api/boost/files/`

**Description:** Retrieve all audio boost files for the authenticated user.

**Request:**
- **Method:** GET
- **Parameters:** None

**Example Request (cURL):**
```bash
curl -X GET http://your-domain.com/api/boost/files/ \
  -b "sessionid=your-session-id"
```

**Success Response (200 OK):**
```json
{
    "files": [
        {
            "id": 789,
            "filename": "quiet_audio.mp3",
            "status": "completed",
            "boost_level": "strong",
            "original_url": "/media/uploads/audio_boost/original/quiet_audio.mp3",
            "boosted_url": "/media/uploads/audio_boost/boosted/quiet_audio_boosted.mp3",
            "uploaded_at": "2024-11-13T13:00:00Z",
            "processed_at": "2024-11-13T13:02:00Z",
            "error_message": null
        }
    ]
}
```

---

### 3.3 Get Audio Boost Status

**Endpoint:** `GET /api/boost/files/<file_id>/status/`

**Description:** Check the processing status of a specific audio boost task.

**Request:**
- **Method:** GET
- **URL Parameters:** 
  - `file_id` (integer): ID of the audio boost file

**Example Request (cURL):**
```bash
curl -X GET http://your-domain.com/api/boost/files/789/status/ \
  -b "sessionid=your-session-id"
```

**Success Response (200 OK):**
```json
{
    "id": 789,
    "filename": "quiet_audio.mp3",
    "status": "completed",
    "boost_level": "strong",
    "original_url": "/media/uploads/audio_boost/original/quiet_audio.mp3",
    "boosted_url": "/media/uploads/audio_boost/boosted/quiet_audio_boosted.mp3"
}
```

---

### 3.4 Delete Audio Boost File

**Endpoint:** `DELETE /api/boost/files/<file_id>/delete/`

**Description:** Delete an audio boost file and its processed version.

**Request:**
- **Method:** DELETE
- **URL Parameters:** 
  - `file_id` (integer): ID of the file to delete

**Example Request (cURL):**
```bash
curl -X DELETE http://your-domain.com/api/boost/files/789/delete/ \
  -H "X-CSRFToken: your-csrf-token" \
  -b "sessionid=your-session-id"
```

**Success Response (200 OK):**
```json
{
    "status": "success"
}
```

---

## 4. Speaker Extraction Service

### 4.1 Upload Files for Speaker Extraction

**Endpoint:** `POST /api/speaker/extract/`

**Description:** Upload a conversation audio file and a target speaker sample to extract the target speaker's voice from the conversation.

**Request:**
- **Method:** POST
- **Content-Type:** multipart/form-data

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| conversation_file | File | Yes | Audio file containing multiple speakers |
| target_speaker_file | File | Yes | Sample audio of the target speaker's voice |
| boost_level | String | No | Volume boost: 'none', '2x', '3x', '4x', '5x' (default: 'none') |

**Example Request (cURL):**
```bash
curl -X POST http://your-domain.com/api/speaker/extract/ \
  -H "X-CSRFToken: your-csrf-token" \
  -F "conversation_file=@/path/to/meeting.mp3" \
  -F "target_speaker_file=@/path/to/speaker_sample.mp3" \
  -F "boost_level=2x" \
  -b "sessionid=your-session-id"
```

**Example Request (Python):**
```python
import requests

url = "http://your-domain.com/api/speaker/extract/"
files = {
    'conversation_file': open('meeting.mp3', 'rb'),
    'target_speaker_file': open('speaker_sample.mp3', 'rb')
}
data = {'boost_level': '2x'}
headers = {'X-CSRFToken': 'your-csrf-token'}
cookies = {'sessionid': 'your-session-id'}

response = requests.post(url, files=files, data=data, headers=headers, cookies=cookies)
print(response.json())
```

**Example Request (JavaScript/Fetch):**
```javascript
const formData = new FormData();
formData.append('conversation_file', conversationFileInput.files[0]);
formData.append('target_speaker_file', targetFileInput.files[0]);
formData.append('boost_level', '2x');

fetch('/api/speaker/extract/', {
    method: 'POST',
    body: formData,
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    },
    credentials: 'same-origin'
})
.then(response => response.json())
.then(data => console.log(data));
```

**Success Response (200 OK):**
```json
{
    "status": "success",
    "message": "Speaker extraction started",
    "file_id": 999
}
```

**Error Responses:**

*400 Bad Request - Missing Files:*
```json
{
    "status": "error",
    "message": "Both conversation file and target speaker file are required"
}
```

*415 Unsupported Media Type:*
```json
{
    "status": "error",
    "message": "Unsupported file type. Please upload MP3, WAV, M4A, or FLAC files."
}
```

---

### 4.2 List Speaker Extraction Files

**Endpoint:** `GET /api/speaker/files/`

**Description:** Retrieve all speaker extraction files for the authenticated user.

**Request:**
- **Method:** GET
- **Parameters:** None

**Example Request (cURL):**
```bash
curl -X GET http://your-domain.com/api/speaker/files/ \
  -b "sessionid=your-session-id"
```

**Success Response (200 OK):**
```json
{
    "files": [
        {
            "id": 999,
            "conversation_filename": "meeting.mp3",
            "target_filename": "speaker_sample.mp3",
            "status": "completed",
            "boost_level": "2x",
            "similarity_score": 77.53,
            "conversation_url": "/media/uploads/speaker_extraction/conversations/meeting.mp3",
            "target_url": "/media/uploads/speaker_extraction/targets/speaker_sample.mp3",
            "extracted_url": "/media/uploads/speaker_extraction/extracted/meeting_extracted.mp3",
            "uploaded_at": "2024-11-13T14:00:00Z",
            "processed_at": "2024-11-13T14:10:00Z",
            "error_message": null
        }
    ]
}
```

**Similarity Score:**
- Range: 0-100
- Higher score indicates better match between extracted voice and target sample
- Typical good matches: 70-90+
- Low scores (<50) may indicate poor extraction quality

---

### 4.3 Delete Speaker Extraction File

**Endpoint:** `DELETE /api/speaker/files/<file_id>/delete/`

**Description:** Delete a speaker extraction task and all associated files.

**Request:**
- **Method:** DELETE
- **URL Parameters:** 
  - `file_id` (integer): ID of the speaker extraction file

**Example Request (cURL):**
```bash
curl -X DELETE http://your-domain.com/api/speaker/files/999/delete/ \
  -H "X-CSRFToken: your-csrf-token" \
  -b "sessionid=your-session-id"
```

**Example Request (JavaScript/Fetch):**
```javascript
fetch(`/api/speaker/files/${fileId}/delete/`, {
    method: 'DELETE',
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    },
    credentials: 'same-origin'
})
.then(response => response.json())
.then(data => console.log(data));
```

**Success Response (200 OK):**
```json
{
    "status": "success",
    "message": "File deleted successfully"
}
```

**Error Response (404 Not Found):**
```json
{
    "status": "error",
    "message": "File not found"
}
```

---

## Common Error Codes

| HTTP Code | Description |
|-----------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters or missing required fields |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 415 | Unsupported Media Type - Invalid file format |
| 500 | Internal Server Error - Server-side error |

---

## Supported Audio Formats

All services support the following audio formats:
- **MP3** (.mp3)
- **WAV** (.wav)
- **M4A** (.m4a)
- **FLAC** (.flac)

**Maximum File Size:** Depends on server configuration (typically 100MB)

---

## Rate Limiting

Currently, there are no hard rate limits implemented. However, please be mindful of:
- Processing queue capacity
- Concurrent file uploads per user
- Server resources

---

## Processing Times

Approximate processing times (may vary based on file size and server load):

| Service | Typical Time | Factors |
|---------|-------------|---------|
| File Denoise | 1-3 minutes | File length, boost level |
| Vocal Separation | 2-5 minutes | File length, complexity |
| Audio Boost | 30 seconds - 2 minutes | File length |
| Speaker Extraction | 3-10 minutes | File length, number of speakers |

---

## WebSocket Support

For real-time processing status updates, consider connecting to WebSocket endpoints (if implemented):

```javascript
const ws = new WebSocket('ws://your-domain.com/ws/processing/');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Processing update:', data);
};
```

---

## Best Practices

1. **File Validation:**
   - Validate file format before upload
   - Check file size limits
   - Ensure audio quality meets your needs

2. **Polling vs WebSockets:**
   - Use status endpoints for occasional checks
   - Use WebSockets for real-time updates
   - Poll every 3-5 seconds to avoid overwhelming the server

3. **Error Handling:**
   - Always check response status codes
   - Display meaningful error messages to users
   - Implement retry logic for failed uploads

4. **Performance:**
   - Compress large files before upload when possible
   - Use appropriate boost/quality settings
   - Clean up old files regularly

---

## Example Integration

### Complete Python Example

```python
import requests
import time

class AudioProcessingClient:
    def __init__(self, base_url, session_id, csrf_token):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.cookies.set('sessionid', session_id)
        self.session.headers.update({'X-CSRFToken': csrf_token})
    
    def denoise_file(self, file_path, boost_level='none'):
        """Upload and process audio file for denoising."""
        url = f"{self.base_url}/api/denoise/upload/"
        files = {'audio_file': open(file_path, 'rb')}
        data = {'boost_level': boost_level}
        
        response = self.session.post(url, files=files, data=data)
        return response.json()
    
    def wait_for_completion(self, file_id, check_interval=5):
        """Wait for file processing to complete."""
        url = f"{self.base_url}/api/denoise/files/{file_id}/status/"
        
        while True:
            response = self.session.get(url)
            data = response.json()
            
            if data['status'] == 'completed':
                print(f"Processing completed! Download: {data['denoised_url']}")
                return data
            elif data['status'] == 'failed':
                print(f"Processing failed: {data.get('error_message')}")
                return None
            
            print(f"Status: {data['status']}... waiting {check_interval}s")
            time.sleep(check_interval)
    
    def list_files(self):
        """Get list of all processed files."""
        url = f"{self.base_url}/api/denoise/files/"
        response = self.session.get(url)
        return response.json()

# Usage
client = AudioProcessingClient(
    base_url="http://your-domain.com",
    session_id="your-session-id",
    csrf_token="your-csrf-token"
)

# Upload file
result = client.denoise_file('my_audio.mp3', boost_level='2x')
file_id = result['file_id']

# Wait for processing
processed = client.wait_for_completion(file_id)
```

---

## Support & Contact

For API support, bug reports, or feature requests, please contact:
- **Email:** support@your-domain.com
- **Documentation:** http://your-domain.com/api/docs/
- **GitHub:** https://github.com/your-repo

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-11-13 | Initial API documentation |

---

## License

This API is proprietary. Unauthorized use is prohibited.
