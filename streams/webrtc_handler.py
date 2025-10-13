"""WebRTC session handling for realtime audio streaming and denoising.

Features:
- Single ingestion loop from broadcaster
- Chunked denoise (2.0s) with overlap (0.5s) using DeepFilterNet2 via dfn2.py
- Per-listener queues for fan-out
- Recording saved to streamed_audios + copied to media/recordings with DB entry
"""
import asyncio
import uuid
from typing import Any, Dict, Optional
from pathlib import Path

import av
import numpy as np
import torch
from django.conf import settings

from aiortc import MediaStreamTrack  # type: ignore
from fractions import Fraction

from df import config as df_config
from df.enhance import enhance


class ListenerAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self._queue = queue
        self._pts = 0
        self._time_base: Optional[Fraction] = None

    async def recv(self):
        audio_arr, sample_rate = await self._queue.get()
        if audio_arr.ndim == 1:
            audio_arr = audio_arr.reshape(1, -1)
        frame = av.AudioFrame.from_ndarray(audio_arr, format="flt", layout="mono")
        frame.sample_rate = sample_rate
        if self._time_base is None:
            self._time_base = Fraction(1, int(sample_rate))
        frame.time_base = self._time_base
        frame.pts = self._pts
        # advance pts by number of samples in frame for pacing
        self._pts += int(audio_arr.shape[-1])
        return frame


class WebRTCSession:
    def __init__(self, session_id: str, username: str, denoise_enabled: bool = True):
        self.session_id = session_id
        self.username = username
        self.denoise_enabled = denoise_enabled

        self.pc = None
        self.ready = asyncio.Event()

        self.listener_queues: Dict[str, asyncio.Queue] = {}
        self.listener_pcs: Dict[str, Any] = {}

        self._consume_task: Optional[asyncio.Task] = None
        self._closed = False

        self._recording_frames: list[np.ndarray] = []
        self._recording_sample_rate: Optional[int] = None
        self.recording_path: Optional[Path] = None

        self._df_model = None
        self._df_state = None
        self._model_sr = None
        # Use settings to allow low-latency tuning
        self._chunk_seconds = float(getattr(settings, 'AUDIO_CHUNK_SECONDS', 0.5))
        self._overlap_seconds = float(getattr(settings, 'AUDIO_OVERLAP_SECONDS', 0.1))
        self._chunk_frames = None
        self._overlap_frames = None
        self._ramp_up = None
        self._ramp_down = None

    async def handle_offer(self, offer_sdp: str) -> str:
        from aiortc import RTCPeerConnection, RTCSessionDescription  # type: ignore

        self.pc = RTCPeerConnection()

        # Init model (via dfn2 cache)
        try:
            import dfn2 as dfn2_module  # type: ignore
            bundle = dfn2_module._init_model(force=False)
        except Exception:
            bundle = __import__("dfn2").dfn2._init_model(force=False)  # type: ignore
        self._df_model = bundle.model
        self._df_state = bundle.df_state
        self._model_sr = df_config("sr", 48000, int, section="df")
        self._chunk_frames = int(self._chunk_seconds * self._model_sr)
        self._overlap_frames = int(self._overlap_seconds * self._model_sr)
        self._ramp_up = (
            torch.linspace(0.0, 1.0, self._overlap_frames) if self._overlap_frames > 0 else None
        )
        self._ramp_down = (
            torch.linspace(1.0, 0.0, self._overlap_frames) if self._overlap_frames > 0 else None
        )

        # Recording path
        streamed_audios_dir = Path(settings.BASE_DIR) / "streamed_audios"
        streamed_audios_dir.mkdir(parents=True, exist_ok=True)
        self.recording_path = streamed_audios_dir / f"{self.username}_{self.session_id}.wav"

        @self.pc.on("track")
        async def on_track(track):
            if track.kind != "audio":
                return
            print(f"Received audio track from {self.username}")

            async def consume():
                pending = np.empty(0, dtype=np.float32)
                prev_tail: Optional[torch.Tensor] = None
                while not self._closed:
                    try:
                        frame = await track.recv()
                        arr = frame.to_ndarray()
                        mono = arr[0] if arr.ndim > 1 else arr
                        if self._recording_sample_rate is None:
                            self._recording_sample_rate = self._model_sr
                        pending = np.concatenate([pending, np.asarray(mono, dtype=np.float32)])

                        while pending.shape[0] >= self._chunk_frames:
                            chunk_np = pending[: self._chunk_frames].copy()
                            if self._overlap_frames > 0:
                                pending = pending[self._chunk_frames - self._overlap_frames :]
                            else:
                                pending = pending[self._chunk_frames :]

                            raw = torch.from_numpy(chunk_np).float().unsqueeze(0)
                            if self.denoise_enabled:
                                try:
                                    enhanced = enhance(self._df_model, self._df_state, raw).cpu().clone()
                                except Exception as e:
                                    print(f"Denoise error: {e}")
                                    enhanced = raw.clone()
                            else:
                                enhanced = raw.clone()

                            segments: list[torch.Tensor] = []
                            if (
                                prev_tail is not None
                                and self._overlap_frames > 0
                                and self._ramp_up is not None
                            ):
                                head = enhanced[:, : self._overlap_frames]
                                cf = prev_tail * self._ramp_down + head * self._ramp_up
                                segments.append(cf)
                                remainder = enhanced[:, self._overlap_frames :]
                                if remainder.numel() > 0:
                                    segments.append(remainder)
                            else:
                                segments.append(enhanced)

                            prev_tail = (
                                enhanced[:, -self._overlap_frames :]
                                if self._overlap_frames > 0
                                else None
                            )

                            for seg in segments:
                                seg_np = seg.squeeze(0).numpy().astype(np.float32)
                                self._recording_frames.append(seg_np.copy())
                                dead = []
                                for lid, q in self.listener_queues.items():
                                    try:
                                        if q.qsize() < 10:
                                            q.put_nowait((seg_np.copy(), self._model_sr))
                                    except Exception:
                                        dead.append(lid)
                                for lid in dead:
                                    self.listener_queues.pop(lid, None)
                    except Exception as e:
                        print(f"Frame consumption ended: {e}")
                        break

                # Flush pending tail
                try:
                    if pending.size > 0:
                        raw = torch.from_numpy(pending.copy()).float().unsqueeze(0)
                        if self.denoise_enabled:
                            try:
                                enhanced = enhance(self._df_model, self._df_state, raw).cpu().clone()
                            except Exception as e:
                                print(f"Denoise error (flush): {e}")
                                enhanced = raw.clone()
                        else:
                            enhanced = raw.clone()

                        if prev_tail is not None and self._overlap_frames and self._overlap_frames > 0:
                            ov = min(self._overlap_frames, enhanced.shape[-1])
                            head = enhanced[:, :ov]
                            ramp_up = (
                                torch.linspace(0.0, 1.0, ov) if ov != self._overlap_frames else self._ramp_up
                            )
                            ramp_down = (
                                torch.linspace(1.0, 0.0, ov) if ov != self._overlap_frames else self._ramp_down
                            )
                            cf = prev_tail[:, -ov:] * ramp_down + head * ramp_up
                            self._recording_frames.append(cf.squeeze(0).numpy().astype(np.float32).copy())
                            remainder = enhanced[:, ov:]
                            if remainder.numel() > 0:
                                self._recording_frames.append(
                                    remainder.squeeze(0).numpy().astype(np.float32).copy()
                                )
                        else:
                            self._recording_frames.append(
                                enhanced.squeeze(0).numpy().astype(np.float32).copy()
                            )
                except Exception as e:
                    print(f"Error flushing pending audio: {e}")

                self.ready.clear()
                await self._save_recording()

            if not self._consume_task:
                self.ready.set()
                self._consume_task = asyncio.create_task(consume())
                print(f"Session {self.session_id} ready: processing loop started")

        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer_sdp, type="offer")
        )
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        return self.pc.localDescription.sdp

    async def create_listener_connection(self, listener_id: str, offer_sdp: str) -> str:
        from aiortc import RTCPeerConnection, RTCSessionDescription  # type: ignore

        try:
            await asyncio.wait_for(self.ready.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            raise Exception("Stream not yet ready (no audio track received)")

        listener_pc = RTCPeerConnection()
        q: asyncio.Queue = asyncio.Queue(maxsize=5)
        self.listener_queues[listener_id] = q
        listener_track = ListenerAudioTrack(q)
        listener_pc.addTrack(listener_track)
        self.listener_pcs[listener_id] = listener_pc

        @listener_pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Listener {listener_id} state: {listener_pc.connectionState}")
            if listener_pc.connectionState in ["failed", "closed"]:
                self.listener_queues.pop(listener_id, None)
                self.listener_pcs.pop(listener_id, None)
                try:
                    await listener_pc.close()
                except Exception:
                    pass

        await listener_pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer_sdp, type="offer")
        )
        answer = await listener_pc.createAnswer()
        await listener_pc.setLocalDescription(answer)
        return listener_pc.localDescription.sdp

    async def _save_recording(self):
        if not self._recording_frames or not self._recording_sample_rate:
            print(f"No audio frames to save for session {self.session_id}")
            return
        try:
            import soundfile as sf
            import shutil
            from datetime import datetime
            from django.core.files import File
            from asgiref.sync import sync_to_async
            from django.contrib.auth import get_user_model
            from .models import StreamRecording

            full_audio = np.concatenate(self._recording_frames)
            sf.write(
                str(self.recording_path), full_audio, self._recording_sample_rate, subtype="PCM_16"
            )
            duration = len(full_audio) / self._recording_sample_rate
            print(
                f"Saved recording to {self.recording_path} (duration: {duration:.2f}s)"
            )

            media_dir = Path(settings.MEDIA_ROOT) / "recordings"
            media_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            media_filename = f"{self.username}_{timestamp}.wav"
            media_path = media_dir / media_filename
            shutil.copy(str(self.recording_path), str(media_path))

            User = get_user_model()

            @sync_to_async
            def create_recording():
                user = User.objects.get(username=self.username)
                rec = StreamRecording.objects.create(
                    owner=user, title=f"Stream {timestamp}", duration=duration
                )
                with open(str(media_path), "rb") as f:
                    rec.file.save(media_filename, File(f), save=True)
                return rec

            await create_recording()
        except Exception as e:
            print(f"Error saving recording: {e}")

    async def close(self):
        print(f"Closing session {self.session_id}")
        await self._save_recording()
        self._closed = True
        if self._consume_task:
            self._consume_task.cancel()
            try:
                await self._consume_task
            except Exception:
                pass
        if self.pc:
            await self.pc.close()
        pcs = list(self.listener_pcs.values())
        self.listener_pcs.clear()
        for pc in pcs:
            try:
                await pc.close()
            except Exception:
                pass
        self.listener_queues.clear()


_sessions: Dict[str, WebRTCSession] = {}


def create_session(username: str, denoise: bool = True) -> WebRTCSession:
    session_id = str(uuid.uuid4())
    session = WebRTCSession(session_id, username, denoise_enabled=denoise)
    _sessions[session_id] = session
    print(
        f"Created session {session_id} for {username} with denoise_enabled={denoise}"
    )
    return session


def get_session(session_id: str) -> Optional[WebRTCSession]:
    return _sessions.get(session_id)


def get_session_by_username(username: str) -> Optional[WebRTCSession]:
    for session in _sessions.values():
        if session.username == username:
            return session
    return None


async def close_session(session_id: str):
    session = _sessions.pop(session_id, None)
    if session:
        await session.close()
