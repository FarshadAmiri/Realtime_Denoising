"""
WebRTC handling with aiortc for real-time audio streaming and processing.
"""
import asyncio
import uuid
from typing import Dict, Optional
from pathlib import Path
from django.conf import settings


def _get_track_class():
    """Lazy load MediaStreamTrack to avoid import at module level."""
    from aiortc import MediaStreamTrack
    import av
    
    class ProcessedAudioTrack(MediaStreamTrack):
        """
        Custom audio track that processes incoming audio through DFN2 denoiser.
        """
        kind = "audio"
        
        def __init__(self, source_track, processor, recorder=None):
            super().__init__()
            self.source = source_track
            self.processor = processor
            self.recorder = recorder
            self.frame_count = 0
        
        async def recv(self):
            """
            Receive and process audio frames.
            """
            try:
                # Get frame from source
                frame = await self.source.recv()
                
                # Convert AudioFrame to numpy array
                audio_array = frame.to_ndarray()
                
                # Process mono channel (take first channel if stereo)
                if audio_array.ndim > 1:
                    audio_mono = audio_array[0]
                else:
                    audio_mono = audio_array
                
                # Denoise the audio
                try:
                    denoised = await self.processor.process_frame(audio_mono)
                except Exception as e:
                    print(f"Error processing audio: {e}")
                    denoised = audio_mono
                
                # Convert back to AudioFrame
                # Ensure proper shape for av.AudioFrame
                if denoised.ndim == 1:
                    denoised = denoised.reshape(1, -1)
                
                processed_frame = av.AudioFrame.from_ndarray(
                    denoised,
                    format='flt',
                    layout='mono'
                )
                processed_frame.sample_rate = frame.sample_rate
                processed_frame.pts = frame.pts
                processed_frame.time_base = frame.time_base
                
                # Record if recorder is available
                if self.recorder:
                    await self.recorder.track(processed_frame)
                
                self.frame_count += 1
                return processed_frame
                
            except Exception as e:
                print(f"Error in ProcessedAudioTrack.recv: {e}")
                raise
    
    return ProcessedAudioTrack


class WebRTCSession:
    """
    Manages a WebRTC session for audio streaming.
    """
    
    def __init__(self, session_id: str, username: str):
        self.session_id = session_id
        self.username = username
        self.pc = None
        self.processor = None
        self.processed_track = None
        self.recorder = None
        self.recording_path: Optional[Path] = None
        self.listeners: Dict[str, any] = {}
    
    async def handle_offer(self, offer_sdp: str) -> str:
        """
        Handle incoming WebRTC offer from broadcaster.
        
        Args:
            offer_sdp: SDP offer string
        
        Returns:
            SDP answer string
        """
        # Lazy imports
        from aiortc import RTCPeerConnection, RTCSessionDescription
        from aiortc.contrib.media import MediaRecorder
        from .audio_processor import get_processor
        
        self.pc = RTCPeerConnection()
        self.processor = get_processor()
        ProcessedAudioTrack = _get_track_class()
        
        # Set up recording
        self.recording_path = Path(settings.MEDIA_ROOT) / 'recordings' / f"{self.session_id}.wav"
        self.recording_path.parent.mkdir(parents=True, exist_ok=True)
        
        @self.pc.on("track")
        async def on_track(track):
            if track.kind == "audio":
                print(f"Received audio track from {self.username}")
                
                # Create recorder for saving processed audio
                self.recorder = MediaRecorder(str(self.recording_path))
                
                # Create processed track
                self.processed_track = ProcessedAudioTrack(
                    track,
                    self.processor,
                    self.recorder
                )
                
                # Add to recorder
                await self.recorder.start()
                
                # Consume frames to trigger processing
                async def consume_frames():
                    try:
                        while True:
                            await self.processed_track.recv()
                    except Exception as e:
                        print(f"Frame consumption ended: {e}")
                
                asyncio.create_task(consume_frames())
        
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state: {self.pc.connectionState}")
            if self.pc.connectionState == "failed" or self.pc.connectionState == "closed":
                await self.close()
        
        # Set remote description
        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer_sdp, type="offer")
        )
        
        # Create answer
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
        
        if not self.processed_track:
            raise Exception("No active stream to listen to")
        
        listener_pc = RTCPeerConnection()
        
        # Add processed audio track to listener connection
        listener_pc.addTrack(self.processed_track)
        
        @listener_pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Listener {listener_id} state: {listener_pc.connectionState}")
            if listener_pc.connectionState in ["failed", "closed"]:
                if listener_id in self.listeners:
                    del self.listeners[listener_id]
        
        # Set remote description
        await listener_pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer_sdp, type="offer")
        )
        
        # Create answer
        answer = await listener_pc.createAnswer()
        await listener_pc.setLocalDescription(answer)
        
        self.listeners[listener_id] = listener_pc
        
        return listener_pc.localDescription.sdp
    
    async def close(self):
        """Close the WebRTC session and cleanup."""
        print(f"Closing session {self.session_id}")
        
        # Stop recorder
        if self.recorder:
            try:
                await self.recorder.stop()
            except Exception as e:
                print(f"Error stopping recorder: {e}")
        
        # Close main peer connection
        if self.pc:
            await self.pc.close()
        
        # Close all listener connections
        for listener_pc in self.listeners.values():
            await listener_pc.close()
        
        self.listeners.clear()


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
