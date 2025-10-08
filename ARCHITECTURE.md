# Architecture Documentation

## System Overview

This document describes the architecture of the Real-time Audio Denoising Web Application.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Browsers                             │
│  ┌──────────────────┐                    ┌──────────────────┐       │
│  │   Alice's Browser│                    │    Bob's Browser  │       │
│  │  (Broadcaster)   │                    │    (Listener)     │       │
│  └────────┬─────────┘                    └─────────┬────────┘       │
└───────────┼────────────────────────────────────────┼────────────────┘
            │                                         │
            │ WebRTC Audio (Offer/Answer)            │ WebRTC Audio
            │ WebSocket (Signaling)                  │ WebSocket
            ▼                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Django Server (ASGI)                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Django Channels Layer                      │   │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────────────┐    │   │
│  │  │ HTTP Views │  │ WebSocket  │  │  WebRTC Handler     │    │   │
│  │  │ (REST API) │  │ Consumers  │  │  (aiortc)           │    │   │
│  │  └─────┬──────┘  └─────┬──────┘  └──────┬──────────────┘    │   │
│  └────────┼───────────────┼────────────────┼───────────────────┘   │
│           │               │                │                        │
│           │               │                ▼                        │
│           │               │     ┌──────────────────────┐            │
│           │               │     │ Audio Processor      │            │
│           │               │     │ (DFN2 Wrapper)       │            │
│           │               │     │  - ThreadPoolExecutor│            │
│           │               │     │  - DeepFilterNet2    │            │
│           │               │     └──────────┬───────────┘            │
│           │               │                │                        │
│           ▼               ▼                ▼                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Django ORM / Database                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │
│  │  │   User   │ │Friendship│ │  Friend  │ │    Stream    │   │   │
│  │  │          │ │          │ │  Request │ │  Recording   │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────┐       ┌──────────────────────────┐    │
│  │    File Storage         │       │   Media Files            │    │
│  │  (Denoised Recordings)  │       │   (WAV files)            │    │
│  └─────────────────────────┘       └──────────────────────────┘    │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Redis Server   │
                  │ (Channel Layer) │
                  └─────────────────┘
```

## Component Details

### 1. Client Layer

#### Browser Components

- **HTML5 Audio API**: Captures microphone input
- **WebRTC (RTCPeerConnection)**: Establishes peer connections
- **WebSocket**: Real-time signaling and presence updates
- **JavaScript Client**: Manages UI and communication

**Key Files:**
- `static/js/webrtc_client.js` - WebRTC abstraction
- `static/js/main.js` - Main page logic
- `static/js/friend_page.js` - Friend page logic

### 2. Server Layer

#### Django Applications

##### Users App (`users/`)
- **Purpose**: User management and friend system
- **Models**:
  - `User` - Custom user with streaming status
  - `FriendRequest` - Friend request tracking
  - `Friendship` - Bidirectional friendship relationships
- **Views**: Authentication, friend search, request handling
- **APIs**: REST endpoints for friend management

##### Streams App (`streams/`)
- **Purpose**: Audio streaming and recording
- **Models**:
  - `StreamRecording` - Stored denoised recordings
  - `ActiveStream` - Currently active streaming sessions
- **Views**: Stream start/stop, WebRTC offer/answer handling
- **Consumers**: WebSocket consumers for signaling
- **WebRTC Handler**: aiortc integration for audio processing

##### Frontend App (`frontend/`)
- **Purpose**: User interface templates
- **Views**: Main page, friend pages
- **Templates**: Base, main, friend page, auth pages

#### Django Channels

- **Protocol Router**: Routes HTTP and WebSocket connections
- **Consumers**:
  - `PresenceConsumer`: Handles friend presence updates
  - `StreamConsumer`: Manages stream signaling
- **Channel Layer**: Redis-backed message passing

### 3. Real-time Processing Pipeline

#### Audio Flow

```
Microphone Input
    ↓
Browser (getUserMedia)
    ↓
WebRTC RTCPeerConnection (Client)
    ↓
[Network - STUN/TURN]
    ↓
aiortc RTCPeerConnection (Server)
    ↓
Audio Track (av.AudioFrame)
    ↓
ProcessedAudioTrack
    ↓
Audio Processor (async)
    ↓
ThreadPoolExecutor
    ↓
DeepFilterNet2 Model
    ↓
Denoised Audio (torch.Tensor)
    ↓
┌──────────┬──────────┐
│          │          │
Recording  │  Listener Output Track
(WAV)      │  (back to WebRTC)
           │
           ↓
       Browser (Remote)
           ↓
       Speakers
```

#### Audio Processor (`streams/audio_processor.py`)

**Class: `DFN2Processor`**

- **Purpose**: Async wrapper for DeepFilterNet2
- **Methods**:
  - `initialize()` - Load model and state
  - `process_frame()` - Async frame processing
  - `_process_frame_sync()` - Sync processing in thread pool
- **Concurrency**: ThreadPoolExecutor for CPU-bound work

**Processing Steps:**
1. Receive raw audio frame (numpy array)
2. Convert to torch tensor
3. Run through DeepFilterNet2 model
4. Apply fade-in/out for smoothness
5. Convert back to numpy array
6. Return denoised audio

### 4. WebRTC Integration

#### Server-Side WebRTC (`streams/webrtc_handler.py`)

**Class: `WebRTCSession`**

- **Purpose**: Manage WebRTC peer connections
- **Responsibilities**:
  - Accept broadcaster offers
  - Create listener connections
  - Route audio through processor
  - Save recordings

**Flow:**

1. **Broadcaster Connects**:
   ```
   Client sends offer → Server creates RTCPeerConnection
   → Server sends answer → Connection established
   → Audio tracks received
   ```

2. **Audio Processing**:
   ```
   Track received → ProcessedAudioTrack created
   → Frames processed through DFN2
   → Saved to recorder
   → Available to listeners
   ```

3. **Listener Connects**:
   ```
   Listener sends offer → Server creates new RTCPeerConnection
   → Server adds ProcessedAudioTrack
   → Server sends answer → Listener receives denoised audio
   ```

### 5. Data Models

#### User Model
```python
User (AbstractUser)
├── username (unique)
├── is_streaming (boolean)
├── last_seen (datetime)
└── password (hashed)
```

#### Friendship System
```python
FriendRequest
├── from_user → User
├── to_user → User
├── status (pending/accepted/rejected)
└── created_at

Friendship
├── user1 → User
├── user2 → User
└── created_at
```

#### Streaming System
```python
StreamRecording
├── owner → User
├── title
├── file (FileField)
├── duration
└── created_at

ActiveStream
├── user → User (OneToOne)
├── session_id
└── started_at
```

### 6. Communication Protocols

#### REST API Communication

- **Authentication**: Session-based (cookies)
- **CSRF Protection**: Token validation
- **Content-Type**: application/json
- **Response Format**: JSON

#### WebSocket Communication

**Presence Updates:**
```json
{
  "type": "streaming_status",
  "username": "alice",
  "is_streaming": true
}
```

**Stream Signaling:**
```json
{
  "type": "offer",
  "offer": { "sdp": "...", "type": "offer" },
  "from_user": "alice"
}
```

#### WebRTC Signaling

**Offer/Answer Exchange:**
```
Client → POST /api/webrtc/offer/
  { "sdp": "...", "type": "offer" }
  
Server → Response
  { "sdp": "...", "type": "answer", "session_id": "..." }
```

### 7. Storage Architecture

#### Database (SQLite/PostgreSQL)
- User accounts and profiles
- Friend relationships
- Stream metadata
- Recording references

#### File System
```
media/
└── recordings/
    ├── session-uuid-1.wav
    ├── session-uuid-2.wav
    └── ...
```

#### Redis
- WebSocket channel routing
- Presence state (optional)
- Session data (optional)

## Security Considerations

### Authentication & Authorization

1. **User Authentication**:
   - Django session-based auth
   - Password hashing (PBKDF2)
   - Login required decorators

2. **Friend Verification**:
   - Check friendship before stream access
   - Validate permissions on all endpoints

3. **CSRF Protection**:
   - CSRF tokens on all POST requests
   - X-CSRFToken header validation

### WebRTC Security

1. **STUN/TURN**:
   - Production requires TURN server
   - Secure WebSocket (WSS) in production

2. **Media Access**:
   - Browser permission for microphone
   - HTTPS required for getUserMedia in production

## Performance Considerations

### Audio Processing

- **Latency**: 200-500ms end-to-end
- **Chunk Size**: 20-100ms frames
- **Model**: DeepFilterNet2 (optimized for real-time)
- **Threading**: ThreadPoolExecutor for parallel processing

### Scaling

1. **Horizontal Scaling**:
   - Multiple Django instances behind load balancer
   - Redis cluster for channel layer
   - Shared media storage (S3, etc.)

2. **Vertical Scaling**:
   - GPU for faster audio processing
   - More CPU cores for ThreadPoolExecutor
   - Increased Redis memory

### Resource Usage

- **CPU**: High during audio processing
- **RAM**: ~500MB per active stream
- **Network**: ~64kbps per audio stream
- **Storage**: ~10MB per minute of recording

## Deployment Architecture (Production)

```
                   ┌─────────────┐
                   │  Nginx      │
                   │  (SSL/WSS)  │
                   └──────┬──────┘
                          │
            ┌─────────────┼─────────────┐
            │                           │
    ┌───────▼────────┐         ┌───────▼────────┐
    │  Daphne/       │         │  Daphne/       │
    │  Uvicorn       │         │  Uvicorn       │
    │  (ASGI)        │         │  (ASGI)        │
    └───────┬────────┘         └───────┬────────┘
            │                           │
            └─────────────┬─────────────┘
                          │
            ┌─────────────▼─────────────┐
            │  PostgreSQL Database      │
            └───────────────────────────┘
            
            ┌───────────────────────────┐
            │  Redis Cluster            │
            └───────────────────────────┘
            
            ┌───────────────────────────┐
            │  S3 / Object Storage      │
            │  (Recordings)             │
            └───────────────────────────┘
```

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | HTML/CSS/JS | User interface |
| WebRTC | aiortc, RTCPeerConnection | Audio streaming |
| Web Framework | Django 4.x | Backend logic |
| ASGI Server | Daphne | Async request handling |
| WebSocket | Django Channels | Real-time communication |
| Message Broker | Redis | Channel layer |
| Database | SQLite/PostgreSQL | Data persistence |
| ML Model | DeepFilterNet2 | Audio denoising |
| Deep Learning | PyTorch | Model runtime |
| Audio Processing | av, numpy | Audio manipulation |
| HTTP Server | Nginx (prod) | Reverse proxy |

## Code Organization

```
Realtime_Denoising/
├── fc25_denoise/          # Django project
│   ├── settings.py        # Configuration
│   ├── urls.py            # URL routing
│   └── asgi.py            # ASGI application
├── users/                 # User management
│   ├── models.py          # User, Friend models
│   ├── views.py           # Auth, friend APIs
│   └── templates/         # Login/register
├── streams/               # Streaming
│   ├── models.py          # Recording models
│   ├── views.py           # Stream APIs
│   ├── consumers.py       # WebSocket handlers
│   ├── webrtc_handler.py  # aiortc integration
│   └── audio_processor.py # DFN2 wrapper
├── frontend/              # UI
│   ├── views.py           # Page views
│   └── templates/         # HTML templates
├── static/                # Static files
│   ├── css/              # Styles
│   └── js/               # JavaScript
├── dfn2.py               # Original denoiser
└── DeepFilterNet2/       # Model checkpoints
```

## Future Enhancements

1. **Scalability**:
   - Microservices architecture
   - Separate processing service
   - GPU cluster for models

2. **Features**:
   - Video streaming
   - Group streams
   - Recording management UI
   - Stream analytics

3. **Performance**:
   - Model quantization
   - Client-side preprocessing
   - Adaptive bitrate
   - Caching strategies

4. **Monitoring**:
   - Prometheus metrics
   - Grafana dashboards
   - Error tracking (Sentry)
   - Performance monitoring
