"""WebRTC handling with aiortc for real-time audio streaming and denoising.

Refactored to:
 - Consume broadcaster audio once
 - Process frames through DeepFilterNet
 - Distribute processed frames to each listener via per-listener queues
 - Provide a MediaStreamTrack abstraction per listener (no duplicate processing)
 - Avoid incorrect MediaRecorder usage (temporarily disable recording until reimplemented safely)
"""
import asyncio
import uuid
from typing import Any, Dict, Optional
from pathlib import Path
from django.conf import settings
import av

from aiortc import MediaStreamTrack  # type: ignore


class ListenerAudioTrack(MediaStreamTrack):
    """A per-listener track that pulls processed frames from its own queue."""
    kind = "audio"

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self._queue = queue

    async def recv(self):
        frame = await self._queue.get()
        return frame


class WebRTCSession:
    """
    Manages a WebRTC session for audio streaming.
    """
    
    def __init__(self, session_id: str, username: str):
        self.session_id = session_id
        self.username = username
        self.pc = None
        self.processor = None
        self.recording_path: Optional[Path] = None
        self.ready = asyncio.Event()
        # Queues for distributing processed frames to listeners (listener_id -> queue)
        self.listener_queues: Dict[str, asyncio.Queue] = {}
        self.listener_pcs: Dict[str, Any] = {}
        # Track consumption task
        self._consume_task: Optional[asyncio.Task] = None
        self._closed = False
    
    async def handle_offer(self, offer_sdp: str) -> str:
        """
        Handle incoming WebRTC offer from broadcaster.
        
        Args:
            offer_sdp: SDP offer string
        
        Returns:
            SDP answer string
        """
        # Lazy imports (kept inside to avoid global aiortc dependency at import time)
        from aiortc import RTCPeerConnection, RTCSessionDescription  # type: ignore
        from .audio_processor import get_processor

        self.pc = RTCPeerConnection()
        self.processor = get_processor()
        # (Recording path reserved for future implementation)
        self.recording_path = Path(settings.MEDIA_ROOT) / 'recordings' / f"{self.session_id}.wav"
        self.recording_path.parent.mkdir(parents=True, exist_ok=True)

        @self.pc.on("track")
        async def on_track(track):
            if track.kind != "audio":
                return
            print(f"Received audio track from {self.username}")

            async def consume():
                while not self._closed:
                    try:
                        frame = await track.recv()
                        audio_array = frame.to_ndarray()
                        if audio_array.ndim > 1:
                            audio_mono = audio_array[0]
                        else:
                            audio_mono = audio_array
                        try:
                            denoised = await self.processor.process_frame(audio_mono)
                        except Exception as e:
                            print(f"Denoise error: {e}")
                            denoised = audio_mono
                        if denoised.ndim == 1:
                            denoised = denoised.reshape(1, -1)
                        processed_frame = av.AudioFrame.from_ndarray(denoised, format='flt', layout='mono')
                        processed_frame.sample_rate = frame.sample_rate
                        processed_frame.time_base = frame.time_base
                        processed_frame.pts = frame.pts
                        # Fan-out to listener queues
                        dead = []
                        for lid, q in self.listener_queues.items():
                            try:
                                if q.qsize() < 5:  # prevent unbounded growth
                                    q.put_nowait(processed_frame)
                            except Exception:
                                dead.append(lid)
                        for lid in dead:
                            self.listener_queues.pop(lid, None)
                    except Exception as e:
                        print(f"Frame consumption ended: {e}")
                        break
                self.ready.clear()

            if not self._consume_task:
                self.ready.set()
                self._consume_task = asyncio.create_task(consume())
                print(f"Session {self.session_id} ready: processing loop started")

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state: {self.pc.connectionState}")
            if self.pc.connectionState in ("failed", "closed"):
                await self.close()

        # Apply remote offer
        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
        # Create and set local answer
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        return self.pc.localDescription.sdp
    
    async def create_listener_connection(self, listener_id: str, offer_sdp: str) -> str:
        """
        Create a peer connection for a listener to receive processed audio.
        
        Args:
            listener_id: Unique identifier for the listener
            offer_sdp: SDP offer from listener
        
        Returns:
            SDP answer string
        """
        from aiortc import RTCPeerConnection, RTCSessionDescription
        import asyncio

        # Wait for readiness (up to 15s)
        try:
            await asyncio.wait_for(self.ready.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            raise Exception("Stream not yet ready (no audio track received)")

        listener_pc = RTCPeerConnection()

        # Create per-listener queue/track
        q: asyncio.Queue = asyncio.Queue(maxsize=5)
        self.listener_queues[listener_id] = q
        listener_track = ListenerAudioTrack(q)

        listener_pc.addTrack(listener_track)
        self.listener_pcs[listener_id] = listener_pc

        @listener_pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Listener {listener_id} state: {listener_pc.connectionState}")
            if listener_pc.connectionState in ["failed", "closed"]:
                # Remove its queue to stop feeding frames
                self.listener_queues.pop(listener_id, None)
                self.listener_pcs.pop(listener_id, None)
                try:
                    await listener_pc.close()
                except Exception:
                    pass

        # Set remote description
        await listener_pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer_sdp, type="offer")
        )

        # Create answer
        answer = await listener_pc.createAnswer()
        await listener_pc.setLocalDescription(answer)
        return listener_pc.localDescription.sdp
    
    async def close(self):
        """Close the WebRTC session and cleanup."""
        print(f"Closing session {self.session_id}")
        
        # Stop processing loop
        self._closed = True
        if self._consume_task:
            self._consume_task.cancel()
            try:
                await self._consume_task
            except Exception:
                pass

        # Close main peer connection
        if self.pc:
            await self.pc.close()
        # Close listener peer connections
        listener_pcs = list(self.listener_pcs.values())
        self.listener_pcs.clear()
        for listener_pc in listener_pcs:
            try:
                await listener_pc.close()
            except Exception:
                pass
        # Clear queues
        self.listener_queues.clear()


# Global session manager
_sessions: Dict[str, WebRTCSession] = {}


def create_session(username: str) -> WebRTCSession:
    """Create a new WebRTC session."""
    session_id = str(uuid.uuid4())
    session = WebRTCSession(session_id, username)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[WebRTCSession]:
    """Get an existing session."""
    return _sessions.get(session_id)


def get_session_by_username(username: str) -> Optional[WebRTCSession]:
    """Get session by username."""
    for session in _sessions.values():
        if session.username == username:
            return session
    return None


async def close_session(session_id: str):
    """Close and remove a session."""
    session = _sessions.pop(session_id, None)
    if session:
        await session.close()
