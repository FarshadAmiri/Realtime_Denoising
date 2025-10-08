# Real-time Audio Denoising Web Application

A Django web application that enables friends to stream live audio to each other with real-time denoising using DeepFilterNet2. Users can broadcast audio that is automatically cleaned of noise, and friends can listen to these live streams or play back saved recordings.

## Features

- **User Authentication**: Register, login, and manage your profile
- **Friend System**: Search for users, send/accept friend requests
- **Real-time Audio Streaming**: Stream your audio with WebRTC
- **Automatic Denoising**: All audio is processed through DeepFilterNet2 for noise reduction
- **Live Listening**: Friends can listen to your live stream in real-time
- **Recording Storage**: Completed streams are saved as denoised recordings
- **Friend Status**: See which friends are currently streaming
- **WebSocket Presence**: Real-time updates of friend streaming status

## Technology Stack

- **Backend**: Django 4.x with Django Channels (ASGI)
- **Real-time Communication**: WebRTC with aiortc (Python)
- **WebSocket**: Channels with Redis for presence and signaling
- **Audio Processing**: DeepFilterNet2 for real-time denoising
- **Frontend**: Django templates with vanilla JavaScript
- **Database**: SQLite (development) / PostgreSQL (production)

## Architecture

1. **Audio Flow**:
   - User's browser captures microphone audio
   - WebRTC sends audio to Django server via aiortc
   - Server processes each audio frame through DeepFilterNet2
   - Denoised audio is relayed to listening friends via WebRTC
   - Processed audio is also saved to file for later playback

2. **Signaling**: WebSocket connections handle:
   - Friend presence updates
   - Streaming status notifications
   - WebRTC offer/answer exchange

## Prerequisites

- Python 3.8+
- Redis server
- CUDA-capable GPU (recommended for best performance)
- Modern web browser with WebRTC support

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/FarshadAmiri/Realtime_Denoising.git
cd Realtime_Denoising
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Note: If you're using CUDA, ensure the torch version matches your CUDA version. The requirements include `torch==2.3.1+cu121` for CUDA 12.1.

### 3. Set up Redis

Install and start Redis:

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
Download and install from https://redis.io/download

### 4. Initialize the database

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Usage

### Getting Started

1. **Register an account** at `/register/`
2. **Login** at `/login/`
3. **Search for friends** using the search box in the left sidebar
4. **Send friend requests** to connect with other users
5. **Accept incoming requests** from the Friend Requests section

### Starting a Stream

1. Click the **"Start Streaming"** button in the left sidebar
2. Allow microphone access when prompted
3. Your audio will be captured, denoised, and made available to friends
4. Friends will see your status change to "Streaming"
5. Click **"Stop Streaming"** when done

### Listening to a Friend's Stream

1. Click on a friend's name in the left sidebar (they must be streaming)
2. On their page, click **"Start Listening"**
3. The denoised live audio will play through your speakers
4. Click **"Stop Listening"** to disconnect

### Playing Recordings

1. Navigate to a friend's page
2. Scroll to the "Previous Recordings" section
3. Click play on any recording to listen to saved denoised audio

## Configuration

### Settings

Key settings in `fc25_denoise/settings.py`:

- `MEDIA_ROOT`: Where recordings are stored (default: `media/`)
- `CHANNEL_LAYERS`: Redis configuration for WebSocket
- `AUTH_USER_MODEL`: Custom user model with streaming fields

### Audio Processing

Audio processing parameters can be adjusted in `streams/audio_processor.py`:

- `max_workers`: Number of threads for parallel processing (default: 4)
- Model sample rate: 48kHz (defined by DeepFilterNet2)

## API Endpoints

### Authentication
- `POST /login/` - Login page
- `POST /register/` - Registration page
- `GET /logout/` - Logout

### Friends
- `GET /api/search/?q=<query>` - Search users
- `GET /api/friends/` - Get friend list
- `POST /api/friend-request/send/` - Send friend request
- `POST /api/friend-request/<id>/respond/` - Accept/reject request
- `GET /api/friend-requests/pending/` - Get pending requests

### Streaming
- `POST /api/stream/start/` - Start streaming
- `POST /api/stream/stop/` - Stop streaming
- `POST /api/webrtc/offer/` - WebRTC broadcaster offer
- `POST /api/webrtc/listen/<username>/` - WebRTC listener offer
- `GET /api/stream/status/<username>/` - Check if user is streaming
- `GET /api/recordings/<username>/` - Get user's recordings

### WebSocket
- `ws://localhost:8000/ws/presence/` - Presence and status updates
- `ws://localhost:8000/ws/stream/<username>/` - Stream signaling

## Project Structure

```
Realtime_Denoising/
├── fc25_denoise/          # Django project settings
│   ├── settings.py        # Main configuration
│   ├── urls.py            # URL routing
│   └── asgi.py            # ASGI configuration with Channels
├── users/                 # User management app
│   ├── models.py          # User, FriendRequest, Friendship models
│   ├── views.py           # Auth and friend API views
│   └── templates/         # Login/register templates
├── streams/               # Audio streaming app
│   ├── models.py          # StreamRecording, ActiveStream models
│   ├── views.py           # Streaming API views
│   ├── consumers.py       # WebSocket consumers
│   ├── routing.py         # WebSocket URL routing
│   ├── audio_processor.py # DFN2 wrapper for async processing
│   └── webrtc_handler.py  # aiortc integration
├── frontend/              # UI app
│   ├── views.py           # Main page and friend page views
│   └── templates/         # HTML templates
├── static/                # Static files
│   ├── css/
│   │   └── style.css      # Application styles
│   └── js/
│       ├── webrtc_client.js  # WebRTC client library
│       ├── main.js           # Main page logic
│       └── friend_page.js    # Friend page logic
├── dfn2.py                # DeepFilterNet2 denoising functions
├── DeepFilterNet2/        # Model checkpoints
├── requirements.txt       # Python dependencies
└── manage.py              # Django management script
```

## Development

### Running Tests

```bash
python manage.py test
```

### Accessing Django Admin

1. Visit `http://localhost:8000/admin/`
2. Login with superuser credentials
3. Manage users, friendships, and recordings

## Deployment Considerations

For production deployment:

1. **Use PostgreSQL** instead of SQLite
2. **Set DEBUG=False** in settings.py
3. **Configure ALLOWED_HOSTS** appropriately
4. **Use Daphne or Uvicorn** as ASGI server
5. **Set up Nginx** as reverse proxy
6. **Configure SSL/TLS** for HTTPS and WSS
7. **Use environment variables** for secrets
8. **Scale Redis** with clustering if needed
9. **Consider GPU servers** for audio processing
10. **Set up media storage** (S3, etc.) for recordings

### Example Production Setup

```bash
# Install production server
pip install daphne

# Run with Daphne
daphne -b 0.0.0.0 -p 8000 fc25_denoise.asgi:application
```

## Performance Notes

- **Latency**: Typical end-to-end latency is 200-500ms depending on:
  - Network conditions
  - Audio chunk size
  - GPU/CPU performance
  
- **Concurrent Streams**: Server can handle multiple streams with:
  - ThreadPoolExecutor for parallel processing
  - Redis for scaling WebSocket connections
  
- **Resource Usage**:
  - CPU/GPU for DeepFilterNet2 processing
  - RAM for buffering audio frames
  - Bandwidth for WebRTC streams

## Troubleshooting

### Redis Connection Error
```
Error: Connection refused
```
**Solution**: Ensure Redis is running: `redis-cli ping` should return `PONG`

### WebRTC Connection Failed
**Solution**: 
- Check firewall settings
- Ensure STUN server is accessible
- For production, configure TURN servers

### Audio Not Playing
**Solution**:
- Grant microphone permissions in browser
- Check browser console for errors
- Verify audio device settings

### Model Loading Error
```
FileNotFoundError: DeepFilterNet2 model not found
```
**Solution**: Ensure `DeepFilterNet2/` directory contains model checkpoints

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

See LICENSE file for details.

## Credits

- **DeepFilterNet2**: Noise suppression model by Schröter et al.
- **Django**: Web framework
- **aiortc**: WebRTC implementation for Python
- **Channels**: Django WebSocket support

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section

## Future Enhancements

Planned features:
- [ ] Video streaming support
- [ ] Group streaming (multiple listeners)
- [ ] Recording titles and descriptions
- [ ] Audio quality selection
- [ ] Mobile app support
- [ ] Advanced user profiles
- [ ] Streaming analytics
