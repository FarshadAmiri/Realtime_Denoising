# Usage Guide: Real-time Audio Denoising Web Application

This guide will walk you through setting up and using the real-time audio denoising web application.

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/FarshadAmiri/Realtime_Denoising.git
cd Realtime_Denoising

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env if needed (defaults should work for local development)

# Run migrations
python manage.py migrate

# Create a superuser (optional, for admin access)
python manage.py createsuperuser
```

### 2. Start Redis

The application requires Redis for WebSocket functionality. Start Redis in a separate terminal:

```bash
# On Ubuntu/Debian
sudo systemctl start redis

# Or run directly
redis-server

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### 3. Start the Application

```bash
# Using Django development server (for testing)
python manage.py runserver

# OR using Daphne (recommended, for WebSocket support)
daphne -b 0.0.0.0 -p 8000 audio_stream_project.asgi:application
```

Visit: http://localhost:8000

## User Walkthrough

### Step 1: Register an Account

1. Click **Register** in the navigation bar
2. Enter a username and password
3. Click **Register** button
4. You'll be automatically logged in and redirected to the home page

### Step 2: Find Friends

1. Click **Find Friends** in the navigation bar
2. Enter a username to search (e.g., "alice" if you created test users)
3. Click the **Add Friend** button next to the user
4. The request is sent and status changes to "Request Sent"

### Step 3: Accept Friend Requests

If you're the recipient:
1. Click **Requests** in the navigation bar
2. View pending requests under "Received Requests"
3. Click **Accept** to accept a friend request
4. You and the other user are now friends!

### Step 4: View Friends List

1. Go to the **Home** page
2. Your friends appear in the left sidebar
3. Each friend shows:
   - Username
   - Status (LIVE badge if streaming, otherwise "Offline")

### Step 5: Start Your Own Stream

1. From the home page, click **Go to My Page**
   - Or visit `/user/your-username/`
2. You'll see the "My Stream" section with controls:
   - **Start Streaming** button
   - **Enable Denoise** toggle (checked by default)
   - Timer (shows 00:00)
3. Click **Start Streaming**
4. Grant microphone permission when prompted by your browser
5. The stream starts:
   - Button changes to "Stop Streaming" (red)
   - Timer starts counting (00:01, 00:02, ...)
   - Your status changes to "LIVE" (friends can see this)
   - Denoise toggle becomes disabled (can't change during stream)

### Step 6: Stop Your Stream

1. Click **Stop Streaming**
2. The stream stops and:
   - Recording is saved automatically
   - Timer stops
   - Status returns to "Offline"
   - Page reloads to show the new recording

### Step 7: Listen to a Friend's Live Stream

1. From the home page, look for friends with the **LIVE** badge
2. Click on a friend's rectangle in the sidebar
3. You're taken to their user page
4. In the "Live Stream" section, click **Start Listening**
5. You'll hear their denoised audio in real-time
6. Click **Stop Listening** when done

### Step 8: View and Play Recordings

On any user page (yours or a friend's):
1. Scroll down to the "Recordings" section
2. Each recording shows:
   - Title (auto-generated with timestamp)
   - Duration (mm:ss format)
   - Creation date
   - Whether denoising was enabled
   - Audio player controls
3. Click the play button on any recording to listen

## Features in Detail

### Real-time Presence

- **WebSocket connection**: Automatically connects when you visit the home page
- **Live updates**: When a friend starts/stops streaming, their status updates immediately
- **No polling**: Uses efficient WebSocket push notifications

### Denoising Control

- **Per-stream setting**: Choose whether to enable denoising when starting a stream
- **DeepFilterNet2**: Uses state-of-the-art deep learning model
- **Server-side processing**: Denoising happens on the server, not your browser
- **Configurable parameters**: Adjust chunk size and overlap in settings

### Friend System

- **Mutual friendship**: Both users must accept friendship
- **Privacy**: Only friends can listen to streams and view recordings
- **Search**: Find users by exact or partial username match
- **Request management**: View sent and received requests separately

### Stream Controls

- **Start/Stop**: Manual control, no auto-start
- **Timer**: Real-time display of stream duration
- **Denoise toggle**: Enable/disable denoising per stream
- **Automatic saving**: Recordings saved on stop or disconnect

### Recordings

- **Automatic naming**: Uses timestamp for easy identification
- **Duration tracking**: Shows exact recording length
- **Metadata**: Tracks whether denoising was enabled
- **Persistent storage**: Stored in `media/recordings/`

## Architecture Notes

### Audio Processing Flow

1. **Broadcaster** starts stream via "Start Streaming" button
2. Browser captures microphone audio via Web Audio API
3. Audio is sent to server in chunks (WebRTC or WebSocket)
4. **Server** processes each chunk:
   - Buffers to configured chunk size (default 2s)
   - Applies DeepFilterNet2 denoising if enabled
   - Applies crossfade between chunks (0.5s overlap)
   - Fans out processed audio to listeners
   - Stores in recording buffer
5. **Listeners** receive denoised audio stream
6. On stop, server finalizes recording and saves to disk

### WebSocket Communication

#### Presence Channel (`/ws/presence/`)
- Broadcasts streaming status updates
- All connected users receive updates
- Automatic reconnection on disconnect

#### Stream Channel (`/ws/stream/<username>/`)
- WebRTC signaling for a specific user's stream
- Only friends can connect
- Used for SDP offer/answer exchange

### REST API Endpoints

#### Stream Control
- `POST /api/stream/start/` - Start streaming
  - Body: `{ "denoise": true }`
  - Returns: `{ "session_id": "...", "status": "started" }`
  
- `POST /api/stream/stop/` - Stop streaming
  - Body: `{ "duration": 123.45 }`
  - Returns: `{ "status": "stopped", "recording_id": 42 }`

#### Stream Status
- `GET /api/stream/status/<username>/`
  - Returns: `{ "is_streaming": true, "session_id": "...", ... }`

#### Recordings
- `GET /api/recordings/` - Your recordings
- `GET /api/recordings/<username>/` - Friend's recordings
  - Returns: `{ "recordings": [...] }`

## Configuration Options

### Environment Variables

Edit `.env` to customize:

```bash
# Django
DEBUG=True
SECRET_KEY=your-secret-key

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Audio Processing
AUDIO_CHUNK_SECONDS=2.0      # Larger = better quality, higher latency
AUDIO_OVERLAP_SECONDS=0.5    # Crossfade duration
AUDIO_SAMPLE_RATE=48000      # Standard for WebRTC
```

### Audio Settings Trade-offs

**Chunk Size (`AUDIO_CHUNK_SECONDS`)**:
- **Smaller (1-2s)**: Lower latency, faster response, more frequent processing
- **Larger (4-8s)**: Better denoising quality, higher latency, fewer chunks

**Overlap (`AUDIO_OVERLAP_SECONDS`)**:
- **Smaller (0.25s)**: More abrupt transitions, less CPU
- **Larger (1s)**: Smoother transitions, more CPU, better quality

**Sample Rate**:
- **48000 Hz**: WebRTC standard, best compatibility
- **16000 Hz**: Lower bandwidth, faster processing, lower quality

## Troubleshooting

### "No active stream" error
- Make sure you clicked "Start Streaming" before trying to stop
- Check browser console for errors
- Verify microphone permissions were granted

### WebSocket connection fails
- Ensure Redis is running: `redis-cli ping`
- Check Redis connection settings in `.env`
- Use Daphne instead of Django development server
- Check browser console for WebSocket errors

### Can't hear friend's stream
- Verify you're friends with the user
- Check the friend is actually streaming (LIVE badge)
- Ensure your browser allows audio autoplay
- Check your audio output settings

### Recordings not appearing
- Wait a few seconds after stopping stream
- Refresh the page
- Check `media/recordings/` directory exists
- Verify disk space is available

### Denoising not working
- Ensure `DeepFilterNet2/` directory exists with model files
- Check if CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`
- View server console for error messages
- Try CPU mode (slower but works without GPU)

## Advanced Usage

### Creating Test Users via Shell

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from users.models import Friendship

# Create users
alice = User.objects.create_user('alice', 'alice@test.com', 'password')
bob = User.objects.create_user('bob', 'bob@test.com', 'password')

# Create friendship
Friendship.objects.create(from_user=alice, to_user=bob, status='accepted')
```

### Inspecting Active Streams

```python
from streams.models import ActiveStream

# List all active streams
for stream in ActiveStream.objects.all():
    print(f"{stream.user.username}: {stream.session_id}")
```

### Viewing Recordings

```python
from streams.models import StreamRecording

# List all recordings
for rec in StreamRecording.objects.all():
    print(f"{rec.owner.username}: {rec.title} ({rec.duration}s)")
```

## Browser Compatibility

### Supported Browsers
- Chrome/Chromium 80+
- Firefox 75+
- Edge 80+
- Safari 14+

### Required Features
- WebSocket support
- WebRTC getUserMedia
- Web Audio API
- ES6 JavaScript

### Known Issues
- Safari may require user interaction before autoplay
- Some Firefox versions have WebRTC audio issues
- Mobile browsers have limited microphone access

## Next Steps

### For Users
1. Invite friends to join the platform
2. Experiment with denoise on/off to hear the difference
3. Listen to friends' recordings
4. Provide feedback on audio quality

### For Developers
1. Implement full WebRTC peer connections
2. Add audio visualizer/waveform display
3. Implement server-side audio ingestion
4. Add recording download option
5. Implement recording titles/descriptions
6. Add user profiles with avatars

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the main README.md for more details
- Review the code documentation in source files
