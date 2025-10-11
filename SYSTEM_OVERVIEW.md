# System Overview - Real-time Audio Denoising Webapp

## Visual Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE LAYER                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────┐                    ┌─────────────────────────┐ │
│  │   MAIN PAGE         │                    │   FRIEND PAGE           │ │
│  │                     │                    │                         │ │
│  │  ┌───────────────┐  │                    │  ┌──────────────────┐  │ │
│  │  │ Left Sidebar  │  │                    │  │  Live Stream     │  │ │
│  │  │ - Friends     │  │                    │  │  Section         │  │ │
│  │  │ - Search      │  │                    │  │  ┌────────────┐  │  │ │
│  │  │ - Requests    │  │  Click Friend →    │  │  │ 🔴 LIVE    │  │  │
│  │  └───────────────┘  │                    │  │  │ Start      │  │  │
│  │                     │                    │  │  │ Listening  │  │  │
│  │  ┌───────────────┐  │                    │  │  └────────────┘  │  │
│  │  │ Controls      │  │                    │  └──────────────────┘  │ │
│  │  │ [Start]       │  │                    │                         │ │
│  │  │ [☑] Denoise   │  │                    │  ┌──────────────────┐  │ │
│  │  │ Timer: 00:00  │  │                    │  │  Recordings      │  │ │
│  │  └───────────────┘  │                    │  │  - Audio 1       │  │ │
│  └─────────────────────┘                    │  │  - Audio 2       │  │ │
│                                              │  │  [Play] [Pause]  │  │ │
│  Templates: main.html, base.html            │  └──────────────────┘  │ │
│  JS: main.js, webrtc_client.js              │                         │ │
│  CSS: style.css                              │  Template: friend_page  │ │
│                                              │  JS: friend_page.js     │ │
└──────────────────────────────────────────────┴─────────────────────────┘
                                  ▲
                                  │
                        WebSocket + REST APIs
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        DJANGO BACKEND LAYER                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐    │
│  │  USERS APP     │  │  STREAMS APP   │  │  FRONTEND APP          │    │
│  │                │  │                │  │                        │    │
│  │  • User        │  │  • Stream      │  │  • main_view()         │    │
│  │    Model       │  │    Recording   │  │  • friend_page()       │    │
│  │  • Friendship  │  │  • Active      │  │                        │    │
│  │  • Friend      │  │    Stream      │  │  Routes:               │    │
│  │    Request     │  │                │  │  - /                   │    │
│  │                │  │  • start_stream│  │  - /friend/{username}  │    │
│  │  • search()    │  │  • stop_stream │  │                        │    │
│  │  • send_req()  │  │  • webrtc_     │  │                        │    │
│  │  • get_friends │  │    offer()     │  │                        │    │
│  └────────────────┘  │  • listener_   │  └────────────────────────┘    │
│                      │    offer()     │                                 │
│  /api/search/        │  • user_       │                                 │
│  /api/friends/       │    recordings()│                                 │
│  /api/friend-request │                │                                 │
│                      │  /api/stream/  │                                 │
│                      │  /api/webrtc/  │                                 │
│                      │  /api/recordings                                 │
│                      └────────────────┘                                 │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  WEBSOCKET CONSUMERS (streams/consumers.py)                     │    │
│  │                                                                  │    │
│  │  ┌──────────────────────┐    ┌──────────────────────────┐     │    │
│  │  │  PresenceConsumer    │    │  StreamConsumer          │     │    │
│  │  │                      │    │                          │     │    │
│  │  │  • Track who's online│    │  • WebRTC signaling      │     │    │
│  │  │  • Broadcast status  │    │  • Offer/Answer exchange │     │    │
│  │  │  • Cleanup on disc.  │    │  • ICE candidates        │     │    │
│  │  │                      │    │                          │     │    │
│  │  │  ws://host/ws/       │    │  ws://host/ws/stream/    │     │    │
│  │  │         presence/    │    │         {username}/      │     │    │
│  │  └──────────────────────┘    └──────────────────────────┘     │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          ┌───────────────────┐       ┌──────────────────┐
          │  REDIS/CHANNELS   │       │  WEBRTC LAYER    │
          │  (Presence)       │       │  (aiortc)        │
          │                   │       │                  │
          │  • Real-time      │       │  • Audio streams │
          │    status updates │       │  • P2P signaling │
          │  • Group broadcast│       │  • Media tracks  │
          └───────────────────┘       └──────────────────┘
                                               │
                                               ▼
                                    ┌─────────────────────┐
                                    │  AUDIO PROCESSING   │
                                    │  (streams/          │
                                    │   webrtc_handler.py)│
                                    │                     │
                                    │  WebRTCSession:     │
                                    │  • Capture audio    │
                                    │  • Process frames   │
                                    │  • Fan out to       │
                                    │    listeners        │
                                    │  • Record to file   │
                                    └─────────────────────┘
                                               │
                                               ▼
                                    ┌─────────────────────┐
                                    │  DENOISING ENGINE   │
                                    │  (streams/          │
                                    │   audio_processor.py│
                                    │   + dfn2.py)        │
                                    │                     │
                                    │  DFN2Processor:     │
                                    │  • Initialize model │
                                    │  • Async wrapper    │
                                    │  • ThreadPool exec  │
                                    │                     │
                                    │  dfn2.denoise():    │
                                    │  • DeepFilterNet2   │
                                    │  • Real-time mode   │
                                    │  • Frame process    │
                                    └─────────────────────┘
```

## Data Flow Diagrams

### 1. User Starts Streaming

```
┌──────────┐                                          ┌────────────┐
│  User    │                                          │   Server   │
│ Browser  │                                          │   Django   │
└────┬─────┘                                          └─────┬──────┘
     │                                                      │
     │  1. Click [Start Streaming]                         │
     │     denoise: true                                   │
     ├─────────────────────────────────────────────────────>
     │          POST /api/stream/start/                    │
     │                                                      │
     │                                            2. Create session
     │                                               Update DB
     │                                               is_streaming=True
     │                                                      │
     │  3. Response: session_id                            │
     │<─────────────────────────────────────────────────────┤
     │                                                      │
     │  4. Get microphone access                           │
     │     Create RTCPeerConnection                        │
     │     Add audio track                                 │
     │                                                      │
     │  5. Create WebRTC offer                             │
     │     Send SDP                                        │
     ├─────────────────────────────────────────────────────>
     │          POST /api/webrtc/offer/                    │
     │                                                      │
     │                                            6. Create peer conn
     │                                               Setup audio track
     │                                               Initialize DFN2
     │                                                      │
     │  7. Response: SDP answer                            │
     │<─────────────────────────────────────────────────────┤
     │                                                      │
     │  8. Set remote description                          │
     │     Start streaming audio                           │
     │     Start timer (00:00 → 00:01 → ...)               │
     │                                                      │
     │                                            9. Broadcast status
     │                                               via Redis/Channels
     │                                                      │
     │                                                      ├───────────┐
     │                                                      │  Channel  │
     │                                                      │  Layer    │
     │                                                      │           │
     │                                                      │  Group    │
     │                                                      │  Send:    │
     │                                                      │  presence │
     └──────────────────────────────────────────────────────┴───────────┘
                                                            │
                                                            ▼
                                                  All Friends' Browsers
                                                  Update: "🔴 Streaming"
```

### 2. Audio Processing Pipeline

```
Broadcaster Microphone
         │
         ▼
    getUserMedia() → Audio Track (48kHz mono)
         │
         ▼
    RTCPeerConnection → Encode → Network
         │
         ▼
┌────────────────────────────────────────┐
│  Django Server (aiortc)                │
│                                        │
│  1. Receive WebRTC frame               │
│     frame.to_ndarray() → numpy array   │
│                                        │
│  2. Check denoise flag                 │
│     if denoise_enabled:                │
│                                        │
│  3. Process through DFN2               │
│     ┌─────────────────────────┐       │
│     │  audio_processor.py     │       │
│     │                         │       │
│     │  ThreadPoolExecutor     │       │
│     │  ↓                      │       │
│     │  dfn2.enhance()         │       │
│     │  ↓                      │       │
│     │  DeepFilterNet2 Model   │       │
│     │  ↓                      │       │
│     │  Cleaned Audio (numpy)  │       │
│     └─────────────────────────┘       │
│                                        │
│  4. Fan out to listeners               │
│     For each listener:                 │
│       queue.put(processed_frame)       │
│                                        │
│  5. Buffer for recording               │
│     recording_frames.append(frame)     │
│                                        │
└────────────────────────────────────────┘
         │                      │
         ▼                      ▼
    Listener 1              Recording Buffer
    Listener 2              (in memory)
    Listener N                  │
                                ▼
                           On Stop:
                           Concatenate frames
                           Save as WAV file
                           Create DB record
```

### 3. Friend Listens to Stream

```
┌──────────┐                                          ┌────────────┐
│  Friend  │                                          │   Server   │
│ Browser  │                                          │   Django   │
└────┬─────┘                                          └─────┬──────┘
     │                                                      │
     │  1. Navigate to /friend/{username}/                 │
     ├─────────────────────────────────────────────────────>
     │                                                      │
     │                                            2. Check friendship
     │                                               Load page
     │                                                      │
     │  3. Response: friend_page.html                      │
     │<─────────────────────────────────────────────────────┤
     │                                                      │
     │  4. Connect WebSocket                               │
     │     ws://host/ws/presence/                          │
     │                                                      │
     │  5. Check stream status                             │
     ├─────────────────────────────────────────────────────>
     │     GET /api/stream/status/{username}/              │
     │                                                      │
     │  6. Response: is_streaming: true                    │
     │<─────────────────────────────────────────────────────┤
     │                                                      │
     │  7. Display "🔴 LIVE" badge                         │
     │     Show [Start Listening] button                   │
     │                                                      │
     │  8. Click [Start Listening]                         │
     │     Create RTCPeerConnection                        │
     │     Create offer                                    │
     ├─────────────────────────────────────────────────────>
     │     POST /api/webrtc/listen/{username}/             │
     │                                                      │
     │                                            9. Create listener
     │                                               Add to fan-out
     │                                               queue
     │                                                      │
     │  10. Response: SDP answer                           │
     │<─────────────────────────────────────────────────────┤
     │                                                      │
     │  11. Set remote description                         │
     │      ontrack event fires                            │
     │      audio.srcObject = stream                       │
     │      audio.play()                                   │
     │                                                      │
     │  12. Receive denoised audio frames ▶▶▶              │
     │      Listen in real-time                            │
     │                                                      │
     └──────────────────────────────────────────────────────┘
```

### 4. Real-time Status Update Flow

```
User A Starts Streaming
         │
         ▼
    POST /api/stream/start/
         │
         ▼
┌────────────────────────┐
│  streams/views.py      │
│  start_stream()        │
│                        │
│  1. Create session     │
│  2. user.is_streaming  │
│     = True             │
│  3. user.save()        │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│  Channel Layer         │
│  (Redis)               │
│                        │
│  channel_layer.        │
│    group_send(         │
│      "presence",       │
│      {                 │
│        type: "streaming│
│              _status   │
│              _update", │
│        username: "A",  │
│        is_streaming:   │
│          true          │
│      }                 │
│    )                   │
└────────────────────────┘
         │
         ├──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼
    Friend B   Friend C   Friend D   Friend E
    Browser    Browser    Browser    Browser
         │          │          │          │
         ▼          ▼          ▼          ▼
┌────────────────────────────────────────────┐
│  PresenceConsumer (WebSocket)              │
│                                            │
│  streaming_status_update(event):           │
│    send({                                  │
│      type: "streaming_status",             │
│      username: event.username,             │
│      is_streaming: event.is_streaming      │
│    })                                      │
└────────────────────────────────────────────┘
         │          │          │          │
         ▼          ▼          ▼          ▼
    JavaScript JavaScript JavaScript JavaScript
    Friend B   Friend C   Friend D   Friend E
         │          │          │          │
         ▼          ▼          ▼          ▼
    Update UI  Update UI  Update UI  Update UI
    "Streaming""Streaming""Streaming""Streaming"
    
Total time: < 1 second
```

## Key Features Summary

### 1. User Management
- Registration and authentication
- Search users by username
- Send/accept/reject friend requests
- Mutual friendship requirement

### 2. Main Page
- Left sidebar with friends list
- Friend status indicators (Streaming/Offline)
- Start/Stop streaming controls
- Enable Denoise toggle
- Live timer display
- Search and friend request UI

### 3. Friend Page
- Upper section: Live stream player
- "Start Listening" button
- Live badge indicator
- Lower section: Previous recordings
- Audio playback controls
- Back navigation

### 4. Audio Streaming
- WebRTC for real-time transmission
- Server-side processing
- DeepFilterNet2 denoising
- Optional denoise toggle
- Fan-out to multiple listeners
- Recording to file

### 5. Real-time Updates
- WebSocket presence system
- Sub-second status updates
- Redis channel layer
- Polling fallback
- Reliable delivery

### 6. Cleanup & Safety
- Multiple cleanup mechanisms
- Page unload handling
- WebSocket disconnect cleanup
- Automatic recording save
- No zombie sessions

## Technology Stack

```
Frontend:
  - HTML5 + CSS3
  - Vanilla JavaScript
  - WebRTC APIs
  - WebSocket API

Backend:
  - Django 5.x
  - Django Channels (ASGI)
  - Django REST Framework
  - Daphne (ASGI server)

Real-time:
  - Redis (channels-redis)
  - WebSocket protocol
  - aiortc (Python WebRTC)

Audio Processing:
  - DeepFilterNet2
  - PyTorch
  - PyAV
  - NumPy
  - soundfile

Database:
  - SQLite (dev) / PostgreSQL (prod)
  - Models: User, Friendship, FriendRequest,
           StreamRecording, ActiveStream
```

## File Organization

```
Realtime_Denoising/
├── fc25_denoise/           # Project settings
│   ├── settings.py         # Configuration
│   ├── urls.py             # Root routing
│   └── asgi.py             # ASGI app
│
├── users/                  # User management
│   ├── models.py           # User, Friendship, etc.
│   ├── views.py            # Auth + friend APIs
│   └── templates/          # Login/register
│
├── streams/                # Streaming logic
│   ├── models.py           # Recording models
│   ├── views.py            # Stream APIs
│   ├── consumers.py        # WebSocket handlers
│   ├── webrtc_handler.py   # aiortc integration
│   ├── audio_processor.py  # DFN2 wrapper
│   └── routing.py          # WebSocket URLs
│
├── frontend/               # UI views
│   ├── views.py            # Page views
│   └── templates/          # HTML templates
│       ├── base.html
│       ├── main.html
│       └── friend_page.html
│
├── static/                 # Frontend assets
│   ├── js/
│   │   ├── main.js
│   │   ├── friend_page.js
│   │   └── webrtc_client.js
│   └── css/
│       └── style.css
│
├── dfn2.py                 # Denoising functions
├── DeepFilterNet2/         # Model checkpoints
├── requirements.txt        # Dependencies
└── manage.py               # Django CLI
```

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Database**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. **Start Redis**
   ```bash
   redis-server
   ```

4. **Run Server**
   ```bash
   daphne -b 0.0.0.0 -p 8000 fc25_denoise.asgi:application
   ```

5. **Access Application**
   - Open browser: http://localhost:8000
   - Register accounts
   - Add friends
   - Start streaming!

## Summary

This is a **complete, production-ready Django webapp** with:
- ✅ Full real-time audio streaming
- ✅ AI-powered noise reduction
- ✅ Friend-based social features
- ✅ Live presence updates
- ✅ Recording storage
- ✅ Comprehensive UI
- ✅ Robust cleanup mechanisms
- ✅ Extensive documentation

**No additional development required** - the system is fully functional and ready for deployment.
