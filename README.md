# Real-time Audio Denoising Web Application

A Django + Channels + WebRTC application for real-time audio streaming with DeepFilterNet2 denoising.

## Features

- **Real-time Audio Streaming**: Stream audio from your microphone to friends with optional denoising
- **Friend System**: Search for users, send friend requests, and build your network
- **Live Presence**: See which friends are currently streaming in real-time
- **Recording Storage**: All streams are automatically saved as denoised audio files
- **WebSocket Integration**: Instant presence updates via Redis-backed Channels
- **WebRTC Support**: Low-latency peer-to-peer audio streaming

## Architecture

### Core Components

1. **Django Apps**:
   - `users`: User authentication and friend management
   - `streams`: Audio streaming, recordings, and WebRTC signaling
   - `core`: Base templates and shared utilities

2. **Audio Processing**:
   - `dfn2.py`: DeepFilterNet2 integration for real-time denoising
   - Configurable chunk size (default 2s) and overlap (default 0.5s)
   - Server-side processing with crossfade between chunks

3. **Communication**:
   - REST API for stream control and data retrieval
   - WebSocket for presence updates and WebRTC signaling
   - Redis backend for Channels layer

### Models

- **User** (Django built-in): User accounts
- **Friendship**: Mutual friendship relationships with pending/accepted/rejected status
- **ActiveStream**: Tracks currently active audio streams
- **StreamRecording**: Stores completed denoised audio recordings

## Setup

### Prerequisites

- Python 3.8+
- Redis server (for Channels)
- CUDA-capable GPU (optional, for faster denoising)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/FarshadAmiri/Realtime_Denoising.git
cd Realtime_Denoising
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Start Redis (in a separate terminal):
```bash
redis-server
```

7. Run the development server:
```bash
python manage.py runserver
```

Or use Daphne for ASGI support:
```bash
daphne -b 0.0.0.0 -p 8000 audio_stream_project.asgi:application
```

8. Visit http://localhost:8000

## Usage

### User Flow

1. **Register/Login**: Create an account or log in
2. **Find Friends**: Search for users by username and send friend requests
3. **Accept Requests**: View and accept friend requests from the "Requests" page
4. **Main Page**: View your friends list with live streaming indicators
5. **Start Streaming**: 
   - Go to your user page
   - Click "Start Streaming"
   - Toggle denoise on/off
   - Stream duration timer shows elapsed time
6. **Listen to Friends**:
   - Click on a friend in the sidebar (or visit their page)
   - If they're live, click "Start Listening"
   - Audio plays in real-time with denoising applied
7. **View Recordings**: All completed streams are saved and listed on user pages

### API Endpoints

#### Authentication
- `POST /login/` - User login
- `POST /register/` - User registration
- `GET /logout/` - User logout

#### Friend Management
- `GET /search/?q=username` - Search for users
- `POST /api/friends/request/` - Send friend request
- `POST /api/friends/accept/` - Accept friend request
- `POST /api/friends/reject/` - Reject friend request
- `GET /friend-requests/` - View pending requests

#### Streaming
- `POST /api/stream/start/` - Start streaming (body: `{denoise: bool}`)
- `POST /api/stream/stop/` - Stop streaming
- `GET /api/stream/status/<username>/` - Get user's streaming status
- `GET /api/recordings/` - List own recordings
- `GET /api/recordings/<username>/` - List user's recordings (if friend)

#### WebSocket Endpoints
- `ws://localhost:8000/ws/presence/` - Presence updates
- `ws://localhost:8000/ws/stream/<username>/` - WebRTC signaling for specific stream

## Configuration

### Environment Variables

- `DEBUG`: Django debug mode (default: True)
- `SECRET_KEY`: Django secret key
- `REDIS_HOST`: Redis server host (default: 127.0.0.1)
- `REDIS_PORT`: Redis server port (default: 6379)
- `AUDIO_CHUNK_SECONDS`: Audio chunk size in seconds (default: 2.0)
- `AUDIO_OVERLAP_SECONDS`: Crossfade overlap in seconds (default: 0.5)
- `AUDIO_SAMPLE_RATE`: Audio sample rate (default: 48000)

### Audio Processing Settings

The denoising pipeline uses the `dfn2.denoise()` function in streaming mode:

```python
result = denoise(
    input_mode="streaming",
    output_path=output_wav,
    chunk_seconds=2.0,        # Configurable via AUDIO_CHUNK_SECONDS
    overlap_seconds=0.5,      # Configurable via AUDIO_OVERLAP_SECONDS
    playback=False,           # Server-side, no local playback
    return_tensor=False,
)
```

## Project Structure

```
Realtime_Denoising/
├── audio_stream_project/    # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── users/                   # User and friendship management
│   ├── models.py
│   ├── views.py
│   ├── admin.py
│   └── templates/
├── streams/                 # Audio streaming and recordings
│   ├── models.py
│   ├── views.py
│   ├── consumers.py         # WebSocket consumers
│   ├── routing.py
│   ├── admin.py
│   └── templates/
├── core/                    # Base templates
│   └── templates/
├── static/                  # Static files (CSS, JS)
├── media/                   # User-uploaded files (recordings)
├── dfn2.py                  # DeepFilterNet2 integration
├── DeepFilterNet2/          # Model files
├── manage.py
└── requirements.txt
```

## Security Considerations

- **CSRF Protection**: All POST requests require CSRF tokens
- **Authentication**: All API endpoints require authentication
- **Friend Verification**: Users can only view/listen to friends' streams
- **Session Management**: Proper session handling for streaming state
- **CORS**: Configured for WebRTC (restrict in production)

## Development Notes

### Testing

Currently, the WebRTC streaming is scaffolded with UI controls. For full implementation:

1. Implement WebRTC peer connections in JavaScript
2. Add server-side audio ingestion from WebRTC tracks
3. Integrate `dfn2.denoise()` in a background worker
4. Stream processed audio back to listeners via WebRTC

### Production Deployment

1. Set `DEBUG=False` in settings
2. Use proper secret key
3. Configure ALLOWED_HOSTS
4. Use PostgreSQL instead of SQLite
5. Serve static files with nginx/whitenoise
6. Use Redis Sentinel for high availability
7. Deploy with Gunicorn + Daphne workers
8. Set up SSL/TLS certificates

## Troubleshooting

### Redis Connection Issues
- Ensure Redis is running: `redis-cli ping` should return `PONG`
- Check Redis connection in settings: `REDIS_HOST` and `REDIS_PORT`

### WebSocket Connection Issues
- Use Daphne or another ASGI server (not Django runserver in production)
- Check browser console for WebSocket errors
- Verify firewall settings allow WebSocket connections

### Audio Denoising Issues
- Ensure DeepFilterNet2 model files are in `./DeepFilterNet2/`
- Check CUDA availability: `python -c "import torch; print(torch.cuda.is_available())"`
- Verify audio chunk settings are appropriate for your use case

## License

This project integrates DeepFilterNet2 for audio denoising. Please refer to the DeepFilterNet2 license for usage terms.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.
