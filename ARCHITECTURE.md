# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT (Browser)                               │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  Login/      │  │   Main Page  │  │  User Page   │                  │
│  │  Register    │  │  (Friends)   │  │  (Stream)    │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│         │                 │                   │                          │
│         └─────────────────┼───────────────────┘                          │
│                           │                                              │
│              ┌────────────┼────────────┐                                 │
│              │            │            │                                 │
│         HTTP/REST    WebSocket    WebRTC                                 │
│              │            │        (Future)                              │
└──────────────┼────────────┼────────────┼─────────────────────────────────┘
               │            │            │
               ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DJANGO APPLICATION (ASGI)                           │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         URL Routing                                 │ │
│  │  /login/, /register/, /, /user/<name>/, /api/stream/*, /api/...   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                           │                                               │
│         ┌─────────────────┼─────────────────┐                            │
│         │                 │                 │                            │
│         ▼                 ▼                 ▼                            │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐                 │
│  │   Views    │  │  Consumers   │  │  Audio          │                 │
│  │  (REST)    │  │ (WebSocket)  │  │  Processor      │                 │
│  │            │  │              │  │                 │                 │
│  │ - Auth     │  │ - Presence   │  │ - Buffering     │                 │
│  │ - Friends  │  │ - Signaling  │  │ - Denoising     │                 │
│  │ - Stream   │  │              │  │ - Crossfade     │                 │
│  │ - Records  │  │              │  │ - Recording     │                 │
│  └─────┬──────┘  └──────┬───────┘  └────────┬────────┘                 │
│        │                │                    │                           │
│        └────────────────┼────────────────────┘                           │
│                         │                                                │
│                         ▼                                                │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                          Models                                     │ │
│  │  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌─────────────────┐ │ │
│  │  │   User   │  │ Friendship │  │  Active  │  │  Stream         │ │ │
│  │  │          │  │            │  │  Stream  │  │  Recording      │ │ │
│  │  └──────────┘  └────────────┘  └──────────┘  └─────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                         │                                                │
└─────────────────────────┼─────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   SQLite/    │  │    Redis     │  │    Media     │
│  PostgreSQL  │  │  (Channels)  │  │    Files     │
│              │  │              │  │              │
│  - Users     │  │  - Presence  │  │  - WAV       │
│  - Friends   │  │  - Sessions  │  │    Files     │
│  - Streams   │  │  - Groups    │  │              │
│  - Records   │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Audio Processing Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         BROADCASTER                                       │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Browser: getUserMedia │
                    │  Capture Microphone    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  WebRTC PeerConnection │
                    │  (Future Implementation)│
                    └───────────┬───────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                            SERVER                                          │
│                                                                            │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │              AudioProcessor Service                             │     │
│   │                                                                 │     │
│   │  1. Buffer Incoming Audio                                      │     │
│   │     ┌──────────────────────────────────────────┐               │     │
│   │     │ Chunk Size: 2.0s (configurable)          │               │     │
│   │     │ Sample Rate: 48kHz                        │               │     │
│   │     └──────────────┬───────────────────────────┘               │     │
│   │                    │                                            │     │
│   │                    ▼                                            │     │
│   │  2. Apply DeepFilterNet2 Denoising                             │     │
│   │     ┌──────────────────────────────────────────┐               │     │
│   │     │ dfn2.enhance(model, df_state, audio)     │               │     │
│   │     │ GPU-accelerated if available              │               │     │
│   │     └──────────────┬───────────────────────────┘               │     │
│   │                    │                                            │     │
│   │                    ▼                                            │     │
│   │  3. Apply Crossfade                                            │     │
│   │     ┌──────────────────────────────────────────┐               │     │
│   │     │ Overlap: 0.5s (configurable)             │               │     │
│   │     │ Linear crossfade between chunks           │               │     │
│   │     └──────────────┬───────────────────────────┘               │     │
│   │                    │                                            │     │
│   └────────────────────┼────────────────────────────────────────────┘     │
│                        │                                                  │
│      ┌─────────────────┼─────────────────┐                               │
│      │                 │                 │                               │
│      ▼                 ▼                 ▼                               │
│  ┌────────┐      ┌──────────┐      ┌────────────┐                       │
│  │ Store  │      │  Fan out │      │  Update    │                       │
│  │ in     │      │  to all  │      │  Stream    │                       │
│  │ Buffer │      │ Listeners│      │  Stats     │                       │
│  └────┬───┘      └─────┬────┘      └──────────────┘                     │
│       │                │                                                 │
└───────┼────────────────┼─────────────────────────────────────────────────┘
        │                │
        ▼                ▼
┌───────────────┐  ┌────────────────────┐
│ Save to File  │  │     LISTENERS      │
│  (on stop)    │  │                    │
│               │  │ ┌────────────────┐ │
│ - WAV format  │  │ │  Receive via   │ │
│ - Denoised    │  │ │  WebSocket/    │ │
│ - Metadata    │  │ │  WebRTC        │ │
└───────────────┘  │ └────────┬───────┘ │
                   │          │         │
                   │          ▼         │
                   │ ┌────────────────┐ │
                   │ │  Play Audio    │ │
                   │ │  (HTML5)       │ │
                   │ └────────────────┘ │
                   └────────────────────┘
```

## WebSocket Communication

```
┌─────────────────┐                    ┌──────────────────┐
│   Client A      │                    │   Client B       │
│  (Broadcaster)  │                    │   (Listener)     │
└────────┬────────┘                    └─────────┬────────┘
         │                                       │
         │   ws://host/ws/presence/              │
         ├───────────────┐      ┌────────────────┤
         │               │      │                │
         │               ▼      ▼                │
         │       ┌─────────────────────┐         │
         │       │  Presence Consumer  │         │
         │       │  (Group: presence)  │         │
         │       └─────────┬───────────┘         │
         │                 │                     │
         │ ◄───────────────┼─────────────────────┤
         │  {"type": "streaming_status_update",  │
         │   "username": "alice",                │
         │   "is_streaming": true}               │
         │                                       │
         │   ws://host/ws/stream/alice/          │
         ├───────────────┐      ┌────────────────┤
         │               │      │                │
         │               ▼      ▼                │
         │       ┌─────────────────────┐         │
         │       │  Stream Consumer    │         │
         │       │ (Group: stream_alice)│        │
         │       └─────────┬───────────┘         │
         │                 │                     │
         │ ─────────────► │                     │
         │  WebRTC Offer   │                     │
         │                 │ ──────────────────► │
         │                 │    WebRTC Offer     │
         │                 │                     │
         │ ◄────────────── │                     │
         │  WebRTC Answer  │ ◄─────────────────  │
         │                 │   WebRTC Answer     │
         └─────────────────┴─────────────────────┘
```

## Data Models

```
┌───────────────────────────────────────────────────────────────┐
│  User (Django Built-in)                                        │
├───────────────────────────────────────────────────────────────┤
│  id: AutoField                                                │
│  username: CharField (unique)                                 │
│  password: CharField (hashed)                                 │
│  email: EmailField                                            │
│  date_joined: DateTimeField                                   │
└───────────────────────────────────────────────────────────────┘
                │
                │ from_user / to_user
                ▼
┌───────────────────────────────────────────────────────────────┐
│  Friendship                                                    │
├───────────────────────────────────────────────────────────────┤
│  id: AutoField                                                │
│  from_user: ForeignKey(User)                                  │
│  to_user: ForeignKey(User)                                    │
│  status: CharField (pending/accepted/rejected)                │
│  created_at: DateTimeField                                    │
│  updated_at: DateTimeField                                    │
│                                                               │
│  Constraints: unique_together(from_user, to_user)             │
│  Methods: are_friends(user1, user2)                           │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│  ActiveStream                                                  │
├───────────────────────────────────────────────────────────────┤
│  id: AutoField                                                │
│  user: OneToOneField(User)                                    │
│  session_id: UUIDField (unique)                               │
│  started_at: DateTimeField                                    │
│  denoise_enabled: BooleanField                                │
└───────────────────────────────────────────────────────────────┘
                │
                │ owner
                ▼
┌───────────────────────────────────────────────────────────────┐
│  StreamRecording                                               │
├───────────────────────────────────────────────────────────────┤
│  id: AutoField                                                │
│  owner: ForeignKey(User)                                      │
│  title: CharField                                             │
│  file: FileField (upload_to='recordings/')                    │
│  duration: FloatField (seconds)                               │
│  denoise_enabled: BooleanField                                │
│  created_at: DateTimeField                                    │
│                                                               │
│  Methods: get_duration_display() -> "MM:SS"                   │
└───────────────────────────────────────────────────────────────┘
```

## Technology Stack Layers

```
┌──────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                         │
│                                                               │
│  HTML5 Templates │ CSS3 │ Vanilla JavaScript │ WebRTC API    │
│  - Django Templates                                           │
│  - Responsive Design                                          │
│  - WebSocket Client                                           │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                          │
│                                                               │
│  Django 5.2 │ Channels 4.0 │ DRF 3.14                        │
│  - URL Routing                                                │
│  - View Logic                                                 │
│  - WebSocket Consumers                                        │
│  - REST API                                                   │
│  - Authentication & Authorization                             │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                      BUSINESS LOGIC                           │
│                                                               │
│  Models │ AudioProcessor │ dfn2.py                            │
│  - User Management                                            │
│  - Friend System                                              │
│  - Stream Management                                          │
│  - Audio Processing                                           │
│  - Recording Storage                                          │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                      DATA LAYER                               │
│                                                               │
│  Django ORM │ Redis │ File System                             │
│  - SQLite (dev) / PostgreSQL (prod)                           │
│  - Redis (channels_redis)                                     │
│  - Media Files                                                │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE                           │
│                                                               │
│  Daphne │ Nginx │ Supervisor │ Let's Encrypt                 │
│  - ASGI Server                                                │
│  - Reverse Proxy                                              │
│  - Process Management                                         │
│  - SSL/TLS                                                    │
└──────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
                        ┌─────────────┐
                        │   Client    │
                        └──────┬──────┘
                               │
                               │ HTTPS (TLS)
                               ▼
                        ┌─────────────┐
                        │   Nginx     │
                        │ (SSL Term)  │
                        └──────┬──────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌──────────┐    ┌──────────┐   ┌──────────┐
        │   HTTP   │    │WebSocket │   │  Static  │
        │  Proxy   │    │  Proxy   │   │  Files   │
        └─────┬────┘    └─────┬────┘   └──────────┘
              │               │
              ▼               ▼
        ┌──────────────────────────┐
        │    Django/Daphne         │
        │                          │
        │  ┌────────────────────┐  │
        │  │  Middleware Stack  │  │
        │  │  - CSRF            │  │
        │  │  - Session         │  │
        │  │  - Auth            │  │
        │  │  - CORS            │  │
        │  └────────────────────┘  │
        │           │              │
        │           ▼              │
        │  ┌────────────────────┐  │
        │  │  Permission Checks │  │
        │  │  - IsAuthenticated │  │
        │  │  - IsFriend        │  │
        │  │  - IsOwner         │  │
        │  └────────────────────┘  │
        └──────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Internet                                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Firewall     │
                    │  (UFW/iptables)│
                    └───────┬───────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                      Server (Ubuntu)                           │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   Nginx      │    │  Supervisor  │    │   Redis      │    │
│  │  (Port 80/   │    │              │    │  (Port 6379) │    │
│  │   443)       │    │  ┌────────┐  │    │              │    │
│  └──────┬───────┘    │  │ Daphne │  │    └──────────────┘    │
│         │            │  │ Worker │  │                         │
│         │            │  │ x2     │  │    ┌──────────────┐    │
│         │            │  └────────┘  │    │ PostgreSQL   │    │
│         │            └──────────────┘    │ (Port 5432)  │    │
│         │                                └──────────────┘    │
│         ▼                                                     │
│  ┌──────────────────────────────┐                            │
│  │  Django Application           │                            │
│  │  /home/audiostream/...        │                            │
│  │                               │                            │
│  │  ┌────────────────────────┐   │                            │
│  │  │  Static Files          │   │                            │
│  │  │  /staticfiles/         │   │                            │
│  │  └────────────────────────┘   │                            │
│  │                               │                            │
│  │  ┌────────────────────────┐   │                            │
│  │  │  Media Files           │   │                            │
│  │  │  /media/recordings/    │   │                            │
│  │  └────────────────────────┘   │                            │
│  └──────────────────────────────┘                            │
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   Logs       │    │   Backups    │    │   Monitoring │    │
│  │ /var/log/... │    │ /backups/... │    │   (Optional) │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

## Request/Response Flow

```
1. User Login
──────────────
Client → POST /login/ → Django View → Authenticate → Session
                                                        │
                                                        ▼
Client ← Redirect to / ──────────────────────────── Set Cookie

2. Load Main Page
─────────────────
Client → GET / → Django View → Query Friends → Render Template
                                    │
                                    ▼
Client ← HTML + JS ←────────────── Include friends list

Client → WebSocket /ws/presence/ → PresenceConsumer → Join group
                                                          │
                                                          ▼
Client ← {"type": "all_statuses"} ←─────────────── Send current status

3. Start Streaming
──────────────────
Client → POST /api/stream/start/ → Create ActiveStream → Broadcast
  (denoise: true)                        │                   │
                                         ▼                   ▼
                              Update DB: session_id    Presence Group
                                         │                   │
Client ← {"session_id": "..."} ←─────────┘                   │
                                                             │
All Clients ← {"is_streaming": true} ←───────────────────────┘

4. Listen to Friend
───────────────────
Client → GET /user/alice/ → Check friendship → Render page
                                  │
                                  ▼
                          Check is_streaming
                                  │
Client ← Show listen button ←─────┘

Client → WebSocket /ws/stream/alice/ → Join stream group
                                              │
Client ← WebRTC signals ←─────────────────────┘

5. Stop Streaming
─────────────────
Client → POST /api/stream/stop/ → Finalize recording → Save file
  (duration: 123.45)                    │                  │
                                        ▼                  ▼
                                Create Recording      Delete ActiveStream
                                        │                  │
Client ← {"recording_id": 42} ←─────────┘                  │
                                                           │
All Clients ← {"is_streaming": false} ←────────────────────┘
```

## Key Components

### Django Apps
- **users**: Authentication, friend management
- **streams**: Streaming, recordings, WebSocket
- **core**: Base templates, shared utilities

### External Services
- **Redis**: Channel layer backend, presence, pub/sub
- **PostgreSQL**: Persistent data storage
- **Nginx**: Reverse proxy, SSL termination, static files

### Audio Components
- **dfn2.py**: DeepFilterNet2 wrapper
- **AudioProcessor**: Buffering, denoising, crossfade
- **DeepFilterNet2**: Neural network model

### Communication
- **HTTP**: REST API, page rendering
- **WebSocket**: Real-time presence, signaling
- **WebRTC**: Peer-to-peer audio (future)

## Scalability Considerations

### Horizontal Scaling
```
┌──────────┐
│   LB     │
└────┬─────┘
     │
     ├─► Worker 1 (Daphne + Django)
     ├─► Worker 2 (Daphne + Django)
     ├─► Worker 3 (Daphne + Django)
     └─► Worker N (Daphne + Django)
          │
          ▼
     ┌─────────┐       ┌──────────┐
     │  Redis  │       │PostgreSQL│
     │ Cluster │       │ Primary/ │
     │         │       │ Replica  │
     └─────────┘       └──────────┘
```

### Performance Optimization
- Connection pooling (DB, Redis)
- Static file CDN
- Query optimization (select_related, prefetch_related)
- Caching (Redis)
- Async processing (Celery for future tasks)
- GPU acceleration (CUDA)

---

For more details, see:
- IMPLEMENTATION_SUMMARY.md - Technical details
- DEPLOYMENT.md - Production setup
- USAGE_GUIDE.md - User instructions
