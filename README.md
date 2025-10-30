# ClearCast: Real-time Audio Streaming with Denoising

Stream audio to your friends with AI-powered noise removal using DeepFilterNet2.

## What it does

- Uses DeepFilterNet2 for the actual denoising.
- Stream your mic audio to friends in real-time (with optional denoising)
- Upload audio files for denoising
- Friend system with requests
- See who's live streaming
- All streams get saved automatically
- Admin panel for managing users and permissions

## Tech Stack

Django + Django Channels + WebRTC + Redis + DeepFilterNet2

The audio processing runs server-side with configurable chunk sizes and overlap for smooth crossfading.

## Setup

**Requirements:**
- Python 3.8+
- Redis
- GPU recommended but not required

**Quick start:**

```bash
# Clone and install
git clone https://github.com/FarshadAmiri/Realtime_Denoising.git
cd Realtime_Denoising
pip install -r requirements.txt

# Setup database
python manage.py migrate
python manage.py createsuperuser

# Start Redis (separate terminal)
redis-server

# Run server
python manage.py runserver
```

## Configuration

You can tweak these in your environment:

- `AUDIO_CHUNK_SECONDS`: Chunk size for processing (default: 2.0)
- `AUDIO_OVERLAP_SECONDS`: Overlap for smooth crossfade (default: 0.5)
- `REDIS_HOST` / `REDIS_PORT`: Redis connection