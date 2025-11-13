# Audio Processing Services - Quick API Reference

## Quick Start

### Authentication
All requests require authentication via session cookies.

```bash
# Login first to get session
curl -X POST http://your-domain.com/login/ \
  -d "username=youruser&password=yourpass"
```

---

## File Denoise

### Upload
```bash
POST /api/denoise/upload/
curl -X POST /api/denoise/upload/ \
  -F "audio_file=@audio.mp3" \
  -F "boost_level=2x"
```

### List Files
```bash
GET /api/denoise/files/
curl -X GET /api/denoise/files/
```

### Check Status
```bash
GET /api/denoise/files/{id}/status/
curl -X GET /api/denoise/files/123/status/
```

### Delete
```bash
DELETE /api/denoise/files/{id}/delete/
curl -X DELETE /api/denoise/files/123/delete/
```

---

## Vocal Separation

### Upload
```bash
POST /api/vocal/separate/
curl -X POST /api/vocal/separate/ \
  -F "audio_file=@song.mp3"
```

### List Files
```bash
GET /api/vocal/files/
curl -X GET /api/vocal/files/
```

### Check Status
```bash
GET /api/vocal/files/{id}/status/
curl -X GET /api/vocal/files/456/status/
```

### Delete
```bash
DELETE /api/vocal/files/{id}/delete/
curl -X DELETE /api/vocal/files/456/delete/
```

---

## Audio Boost

### Upload
```bash
POST /api/boost/upload/
curl -X POST /api/boost/upload/ \
  -F "audio_file=@quiet.mp3" \
  -F "boost_level=strong"
```

**Boost Levels:** `gentle`, `medium`, `strong`, `max`

### List Files
```bash
GET /api/boost/files/
curl -X GET /api/boost/files/
```

### Check Status
```bash
GET /api/boost/files/{id}/status/
curl -X GET /api/boost/files/789/status/
```

### Delete
```bash
DELETE /api/boost/files/{id}/delete/
curl -X DELETE /api/boost/files/789/delete/
```

---

## Speaker Extraction

### Upload
```bash
POST /api/speaker/extract/
curl -X POST /api/speaker/extract/ \
  -F "conversation_file=@meeting.mp3" \
  -F "target_speaker_file=@sample.mp3" \
  -F "boost_level=2x"
```

### List Files
```bash
GET /api/speaker/files/
curl -X GET /api/speaker/files/
```

### Delete
```bash
DELETE /api/speaker/files/{id}/delete/
curl -X DELETE /api/speaker/files/999/delete/
```

---

## Response Formats

### Success
```json
{
    "status": "success",
    "message": "...",
    "file_id": 123
}
```

### Error
```json
{
    "status": "error",
    "message": "Error description"
}
```

### File List
```json
{
    "files": [
        {
            "id": 123,
            "filename": "audio.mp3",
            "status": "completed",
            "original_url": "/media/.../original.mp3",
            "processed_url": "/media/.../processed.mp3"
        }
    ]
}
```

---

## Status Values

- `pending` - Waiting for processing
- `processing` - Currently being processed
- `completed` - Successfully processed
- `error`/`failed` - Processing failed

---

## Supported Formats

MP3, WAV, M4A, FLAC

---

## HTTP Status Codes

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `415` - Unsupported Media Type
- `500` - Server Error
