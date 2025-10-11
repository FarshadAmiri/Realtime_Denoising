# System Architecture - Real-time Denoised Audio Streaming

## Overall System Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         User Interface (Browser)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐         ┌──────────────────┐                    │
│  │  Main Page       │         │  Friend Page     │                    │
│  │  - Start Stream  │         │  - Listen to     │                    │
│  │  - Timer Display │         │    Friend Stream │                    │
│  │  - Friends List  │         │  - View          │                    │
│  │                  │         │    Recordings    │                    │
│  └──────────────────┘         └──────────────────┘                    │
│         │                              │                               │
│         │                              │                               │
│         ├──────────────┬───────────────┤                               │
│         │              │               │                               │
│         ▼              ▼               ▼                               │
│  ┌──────────────────────────────────────────────┐                     │
│  │         WebRTC Client (JavaScript)           │                     │
│  │  - startBroadcast() → Capture Microphone     │                     │
│  │  - startListening() → Receive Audio          │                     │
│  │  - WebSocket for Status Updates              │                     │
│  └──────────────────────────────────────────────┘                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                            │                │
                            │ WebRTC         │ WebSocket
                            │ (Audio)        │ (Status)
                            ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Django/Channels Server (ASGI)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                  REST API Views (streams/views.py)                │ │
│  │                                                                   │ │
│  │  POST /api/stream/start/    → Create WebRTC session             │ │
│  │  POST /api/stream/stop/     → Stop & save recording             │ │
│  │  POST /api/webrtc/offer/    → Handle broadcaster SDP            │ │
│  │  POST /api/webrtc/listen/   → Handle listener SDP               │ │
│  │  GET  /api/stream/status/   → Check streaming status            │ │
│  │  GET  /api/recordings/      → List saved recordings             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                            │                                            │
│                            ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │          WebRTC Handler (streams/webrtc_handler.py)              │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │              WebRTCSession Class                            │ │ │
│  │  │                                                             │ │ │
│  │  │  • Broadcaster Connection (aiortc.RTCPeerConnection)       │ │ │
│  │  │  • Listener Connections (multiple peer connections)        │ │ │
│  │  │  • Audio Frame Processing Loop                             │ │ │
│  │  │  • Frame Buffering for Recording                           │ │ │
│  │  │  • Fan-out to Listener Queues                              │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                            │                                      │ │
│  │                            ▼                                      │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │    Audio Processor (streams/audio_processor.py)             │ │ │
│  │  │                                                             │ │ │
│  │  │    • DFN2Processor class                                    │ │ │
│  │  │    • Uses DeepFilterNet2 model (dfn2.py)                    │ │ │
│  │  │    • Real-time audio denoising                              │ │ │
│  │  │    • Thread pool executor for async processing              │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │        WebSocket Consumers (streams/consumers.py)                │ │
│  │                                                                   │ │
│  │  • PresenceConsumer    → Track user presence & streaming        │ │
│  │  • StreamConsumer      → Signaling for WebRTC                   │ │
│  │  • Real-time status broadcasts                                  │ │
│  │  • Disconnect cleanup (NEW)                                     │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                            │                                            │
│                            ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │             Channel Layer (Redis / InMemory)                      │ │
│  │                                                                   │ │
│  │  • Pub/Sub for WebSocket broadcasts                              │ │
│  │  • "presence" group for status updates                           │ │
│  │  • Instant friend status propagation                             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                            │                │
                            │ Read/Write     │ Read/Write
                            ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Data Storage Layer                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────┐    ┌──────────────────────────────────┐  │
│  │   SQLite Database       │    │   File System                    │  │
│  │                         │    │                                  │  │
│  │  • User                 │    │  streamed_audios/                │  │
│  │  • Friendship           │    │  └─ username_sessionid.wav       │  │
│  │  • FriendRequest        │    │                                  │  │
│  │  • StreamRecording      │    │  media/recordings/               │  │
│  │  • ActiveStream         │    │  └─ username_timestamp.wav       │  │
│  │                         │    │     (accessible via web)         │  │
│  └─────────────────────────┘    └──────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Audio Processing Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Broadcaster (User A)                              │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Microphone Audio
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  WebRTC getUserMedia() → Capture Audio Stream                            │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Raw Audio Frames
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  RTCPeerConnection → Send to Server (WebRTC SRTP)                        │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Server: aiortc.RTCPeerConnection.ontrack()                              │
│  → Receive AudioFrame (av.AudioFrame)                                    │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Convert to numpy array                                                  │
│  → frame.to_ndarray() → audio_array                                      │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  DeepFilterNet2 Processing (dfn2.py)                                     │
│  → processor.process_frame(audio_array)                                  │
│  → Enhanced/denoised audio                                               │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
         ┌──────────────┐  ┌─────────────┐  ┌──────────────┐
         │ Recording    │  │ Listener 1  │  │ Listener 2   │
         │ Buffer       │  │ Queue       │  │ Queue        │
         │              │  │             │  │              │
         │ Store frame  │  │ Put frame   │  │ Put frame    │
         │ for later    │  │ in queue    │  │ in queue     │
         └──────────────┘  └─────────────┘  └──────────────┘
                │                  │                  │
                │ On Stop          │                  │
                ▼                  ▼                  ▼
         ┌──────────────┐  ┌─────────────┐  ┌──────────────┐
         │ Concatenate  │  │ Send via    │  │ Send via     │
         │ all frames   │  │ WebRTC to   │  │ WebRTC to    │
         │              │  │ Friend 1    │  │ Friend 2     │
         ▼              │  └─────────────┘  └──────────────┘
┌─────────────────────────────────────────────────────────────────┐
│  Save to WAV file                                               │
│  → streamed_audios/username_sessionid.wav                       │
│  → media/recordings/username_timestamp.wav                      │
│  → Create StreamRecording database entry                        │
└─────────────────────────────────────────────────────────────────┘
```

## Cleanup Mechanisms (New Implementation)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Cleanup Trigger Events                              │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         │                    │                    │
         ▼                    ▼                    ▼
    ┌────────┐         ┌──────────┐        ┌────────────┐
    │ Page   │         │ WebSocket│        │ Tab Close  │
    │ Reload │         │ Disconnect│        │ / Browser  │
    │ (F5)   │         │          │        │ Close      │
    └────────┘         └──────────┘        └────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    ┌────────────────────────────────────────────────────┐
    │       beforeunload Event Handler                   │
    │       navigator.sendBeacon()                       │
    │       → POST /api/stream/stop/                     │
    └────────────────────────────────────────────────────┘
         │                    │                    │
         │                    ▼                    │
         │         ┌──────────────────────┐        │
         │         │ PresenceConsumer     │        │
         │         │ .disconnect()        │        │
         │         │ → cleanup_user_      │        │
         │         │   stream()           │        │
         │         └──────────────────────┘        │
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  Close WebRTC Session                    │
         │  → async close_session(session_id)       │
         └──────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  Save Recording (if frames exist)        │
         │  → _save_recording()                     │
         │  → Concatenate frames                    │
         │  → Save WAV file                         │
         │  → Create DB record                      │
         └──────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  Cleanup Resources                       │
         │  • Close RTCPeerConnection               │
         │  • Close listener connections            │
         │  • Clear frame buffers                   │
         │  • Delete ActiveStream DB entry          │
         │  • Update User.is_streaming = False      │
         └──────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  Notify Friends                          │
         │  → channel_layer.group_send()            │
         │  → "presence" group                      │
         │  → streaming_status_update               │
         │     {username, is_streaming: false}      │
         └──────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  Friends' Browsers Update UI             │
         │  → Status changes from "Streaming"       │
         │     to "Offline"                         │
         │  → Live player hidden                    │
         │  → Recording available in list           │
         └──────────────────────────────────────────┘
```

## Real-time Status Update Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  User A clicks "Start Streaming"                                        │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  POST /api/stream/start/                 │
         │  → Create WebRTC session                 │
         │  → User.is_streaming = True              │
         │  → Create ActiveStream entry             │
         └──────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  channel_layer.group_send()              │
         │  → Group: "presence"                     │
         │  → Type: "streaming_status_update"       │
         │  → Data: {username, is_streaming: true}  │
         │                                          │
         │  [Redis Log]                             │
         │  "Sending streaming_status_update        │
         │   via channel layer for user alice"      │
         └──────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  Redis Pub/Sub                           │
         │  → Broadcast to all channel subscribers  │
         └──────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  All PresenceConsumers receive message   │
         │                                          │
         │  [Redis Log]                             │
         │  "PresenceConsumer received              │
         │   streaming_status_update: alice         │
         │   is_streaming=True"                     │
         └──────────────────────────────────────────┘
                              │
                              ▼
         ┌──────────────────────────────────────────┐
         │  WebSocket send to all connected clients │
         │  → JSON: {type: "streaming_status",      │
         │           username: "alice",             │
         │           is_streaming: true}            │
         └──────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
         ┌──────────┐  ┌──────────┐  ┌──────────┐
         │ Friend 1 │  │ Friend 2 │  │ Friend 3 │
         │ Browser  │  │ Browser  │  │ Browser  │
         │          │  │          │  │          │
         │ Update   │  │ Update   │  │ Update   │
         │ UI:      │  │ UI:      │  │ UI:      │
         │ "alice:  │  │ "alice:  │  │ "alice:  │
         │ Streaming"│  │ Streaming"│  │ Streaming"│
         └──────────┘  └──────────┘  └──────────┘
              │             │             │
              ▼             ▼             ▼
         Status badge changes color & text
         "Streaming" badge appears
         Listen button becomes available
         
         Time: < 1 second from button click
```

## Key Improvements Summary

### 1. Timer Implementation
```
Before:
┌──────────────────────┐
│ Timer stuck at 00:00 │
│ Element not found    │
└──────────────────────┘

After:
┌────────────────────────────────┐
│ Robust element checking        │
│ → Find element on every update │
│ → Debug logging enabled        │
│ → Updates every 1 second       │
│ Result: 00:01, 00:02, 00:03... │
└────────────────────────────────┘
```

### 2. Recording Implementation
```
Before:
┌──────────────────────────────────┐
│ Frames processed and discarded   │
│ No file saved                    │
│ streamed_audios/ empty           │
└──────────────────────────────────┘

After:
┌──────────────────────────────────┐
│ Frames buffered in memory        │
│ → On stop: concatenate frames    │
│ → Save to WAV file               │
│ → Create database record         │
│ → Available for playback         │
│ Result: WAV files in folder      │
└──────────────────────────────────┘
```

### 3. Cleanup Implementation
```
Before:
┌──────────────────────────────────┐
│ Page reload → stream continues   │
│ Tab close → session remains      │
│ Disconnect → no cleanup          │
│ Result: Zombie sessions          │
└──────────────────────────────────┘

After:
┌──────────────────────────────────┐
│ beforeunload → sendBeacon        │
│ Tab close → WebSocket disconnect │
│ Disconnect → cleanup_user_stream │
│ Result: Consistent cleanup       │
└──────────────────────────────────┘
```

### 4. Status Update Speed
```
Before:
┌──────────────────────────────────┐
│ Polling every 5-8 seconds        │
│ Delayed status updates           │
│ Friends see stale status         │
└──────────────────────────────────┘

After:
┌──────────────────────────────────┐
│ WebSocket instant updates        │
│ + 3s polling as backup           │
│ Status change: < 1 second        │
│ Result: Real-time experience     │
└──────────────────────────────────┘
```

---

**Legend:**
- `→` : Data flow direction
- `│` : Vertical flow
- `▼` : Continues below
- `┌─┐` : Component boundary
- `[ ]` : Log entry or note
