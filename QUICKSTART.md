# Quick Start Guide

This guide will help you get the Real-time Audio Denoising Web Application up and running quickly.

## Prerequisites

- Python 3.8 or higher
- Redis server
- (Optional) CUDA-capable GPU for better performance

## Installation Steps

### 1. Install Redis

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows:**
- Download from https://redis.io/download
- Or use WSL2 with Ubuntu instructions

### 2. Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Note:** If you encounter issues with torch installation, install it separately based on your system:

```bash
# For CUDA 12.1
pip install torch==2.3.1+cu121 torchaudio==2.3.1+cu121 --extra-index-url https://download.pytorch.org/whl/cu121

# For CPU only
pip install torch==2.3.1 torchaudio==2.3.1 --extra-index-url https://download.pytorch.org/whl/cpu
```

### 3. Initialize Database

The migrations have already been created. Just apply them:

```bash
python manage.py migrate
```

### 4. Create Demo Users (Optional)

To quickly test the application, create some demo users:

```bash
python setup_demo.py
```

This creates three users:
- **alice** (password: demo123) - friends with bob and charlie
- **bob** (password: demo123) - friends with alice
- **charlie** (password: demo123) - friends with alice

Or create your own superuser:

```bash
python manage.py createsuperuser
```

### 5. Start Redis

Make sure Redis is running:

```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG
```

If not running:
```bash
redis-server
```

### 6. Start the Django Server

```bash
python manage.py runserver
```

The server will start on http://localhost:8000

## Testing the Application

### 1. Open Browser

Navigate to http://localhost:8000 in your browser.

You'll be redirected to the login page.

### 2. Login or Register

- Use demo credentials (alice/demo123, bob/demo123, etc.)
- Or register a new account at http://localhost:8000/register/

### 3. Add Friends

1. After logging in, use the search box in the left sidebar
2. Search for other users
3. Click "Add Friend" to send a friend request
4. The recipient can accept the request from their "Friend Requests" section

### 4. Start Streaming

1. Click the "Start Streaming" button
2. Allow microphone access when prompted by your browser
3. Your audio will be captured and made available to friends
4. The audio is automatically processed through DeepFilterNet2 for noise reduction

### 5. Listen to a Friend's Stream

1. When a friend is streaming, their status shows "🔴 Streaming"
2. Click on their name in the friends list
3. On their page, click "Start Listening"
4. You'll hear their denoised audio in real-time

### 6. Play Recordings

- Completed streams are automatically saved
- Navigate to a friend's page
- Scroll to "Previous Recordings"
- Click play on any recording to listen

## Architecture Overview

```
Browser (Alice)                  Django Server                     Browser (Bob)
     |                                |                                  |
     |-- Microphone Audio -------> WebRTC ----> DeepFilterNet2          |
     |                              (aiortc)         |                   |
     |                                |              v                   |
     |                                |         Denoised Audio           |
     |                                |              |                   |
     |                                |              +---> Save WAV      |
     |                                |              |                   |
     |                                |              +---> WebRTC ----->|--- Speakers
     |                                |                   (aiortc)       |
     |                                |                                  |
     |<--- WebSocket (Status) -----> Redis <--- WebSocket (Status) ----|
```

## API Endpoints

### Authentication
- `GET /login/` - Login page
- `GET /register/` - Registration page
- `GET /logout/` - Logout

### Main Pages
- `GET /` - Main page with friends list
- `GET /friend/<username>/` - Friend's page with stream and recordings

### REST APIs
- `GET /api/friends/` - Get your friends list
- `GET /api/search/?q=<query>` - Search for users
- `POST /api/friend-request/send/` - Send friend request
- `POST /api/friend-request/<id>/respond/` - Accept/reject request
- `POST /api/stream/start/` - Start streaming
- `POST /api/stream/stop/` - Stop streaming
- `POST /api/webrtc/offer/` - WebRTC broadcaster offer
- `POST /api/webrtc/listen/<username>/` - WebRTC listener offer
- `GET /api/recordings/<username>/` - Get user's recordings

### WebSocket Endpoints
- `ws://localhost:8000/ws/presence/` - Friend presence updates
- `ws://localhost:8000/ws/stream/<username>/` - Stream signaling

## Troubleshooting

### Redis Connection Error

**Error:** `Error connecting to Redis`

**Solution:**
```bash
# Start Redis
redis-server

# Check if running
redis-cli ping
```

### Microphone Access Denied

**Error:** Browser doesn't request microphone access

**Solution:**
- Make sure you're using HTTPS in production
- For localhost, HTTP is fine
- Check browser permissions: chrome://settings/content/microphone
- Try a different browser

### WebRTC Connection Failed

**Error:** Can't connect to stream

**Solution:**
- Check firewall settings
- Ensure both users are on the same network (for testing)
- For production, configure TURN servers
- Check browser console for detailed errors

### Audio Processing Errors

**Error:** `Error processing audio`

**Solution:**
- Ensure DeepFilterNet2 model files are in `DeepFilterNet2/` directory
- Check GPU/CUDA availability: `torch.cuda.is_available()`
- Try CPU mode if GPU unavailable
- Check logs for detailed error messages

### Database Errors

**Error:** `no such table: users_user`

**Solution:**
```bash
# Run migrations
python manage.py migrate
```

## Development Tips

### Django Admin

Access the admin interface at http://localhost:8000/admin/

Create a superuser:
```bash
python manage.py createsuperuser
```

### Viewing Logs

```bash
# Django logs appear in console
python manage.py runserver

# Check Redis logs
redis-cli monitor
```

### Testing Without Audio

You can test the UI and friend system without starting streams:
1. Create users and friendships
2. Navigate through the interface
3. Check API endpoints with tools like Postman

## Next Steps

- Read the full README.md for detailed documentation
- Explore the code structure
- Customize the UI in `static/css/style.css`
- Add more features (see README Future Enhancements section)

## Support

For issues:
1. Check this quickstart guide
2. Review the main README.md
3. Check the troubleshooting section
4. Open an issue on GitHub

## Security Notes

**Important for Production:**
- Change `SECRET_KEY` in settings.py
- Set `DEBUG = False`
- Configure `ALLOWED_HOSTS`
- Use environment variables for sensitive data
- Set up HTTPS/WSS
- Use PostgreSQL instead of SQLite
- Configure proper CORS settings
- Set up authentication rate limiting
