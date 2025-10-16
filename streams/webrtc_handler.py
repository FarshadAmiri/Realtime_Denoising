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
import time

from aiortc import MediaStreamTrack  # type: ignore
from fractions import Fraction

from df import config as df_config
from df.enhance import enhance
from av.audio.resampler import AudioResampler
import re


class ListenerAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self._queue = queue
        self._pts = 0
        self._time_base: Optional[Fraction] = None
        self._buffer = np.empty(0, dtype=np.float32)
        self._sample_rate: Optional[int] = None
        self._frame_len: Optional[int] = None  # samples per 20ms at sample_rate
        self._t0: Optional[float] = None  # wall clock reference

    async def recv(self):
        # Ensure we have enough samples to produce a ~20ms frame
        while self._frame_len is None or self._buffer.shape[0] < self._frame_len:
            chunk, sample_rate = await self._queue.get()
            if self._sample_rate is None:
                self._sample_rate = int(sample_rate)
                self._time_base = Fraction(1, self._sample_rate)
                self._frame_len = max(1, int(self._sample_rate * 0.02))  # ~20ms
            # append to buffer
            self._buffer = np.concatenate([self._buffer, chunk.astype(np.float32)])

        # Slice one frame
        out = self._buffer[: self._frame_len]
        self._buffer = self._buffer[self._frame_len :]

        # Convert float32 [-1,1] to int16 for better encoder compatibility
        out_i16 = np.clip(out * 32767.0, -32768, 32767).astype(np.int16)
        out_i16 = out_i16.reshape(1, -1)  # mono

        frame = av.AudioFrame.from_ndarray(out_i16, format="s16", layout="mono")
        frame.sample_rate = self._sample_rate
        frame.time_base = self._time_base
        frame.pts = self._pts
        self._pts += self._frame_len
        # Real-time pacing: align to wall clock based on pts / sample_rate
        if self._t0 is None:
            self._t0 = time.monotonic()
        else:
            target = self._t0 + (frame.pts / self._sample_rate)
            now = time.monotonic()
            delay = target - now
            if delay > 0:
                try:
                    await asyncio.sleep(delay)
                except Exception:
                    pass
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
        self._chunk_seconds = float(getattr(settings, 'AUDIO_CHUNK_SECONDS', 4))
        self._overlap_seconds = float(getattr(settings, 'AUDIO_OVERLAP_SECONDS', 0.5))
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
        self._ramp_up = torch.linspace(0.0, 1.0, self._overlap_frames) if self._overlap_frames > 0 else None
        self._ramp_down = torch.linspace(1.0, 0.0, self._overlap_frames) if self._overlap_frames > 0 else None

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
                        # Initialize resampler once per track
                        if not hasattr(track, '_df_resampler') or track._df_resampler is None:
                            track._df_resampler = AudioResampler(format='s16', layout='mono', rate=int(self._model_sr))
                        out_frames = track._df_resampler.resample(frame)
                        if not isinstance(out_frames, (list, tuple)):
                            out_frames = [out_frames]
                        for of in out_frames:
                            arr = of.to_ndarray()
                            if arr.ndim == 2:
                                arr = arr.reshape(-1)
                            mono = (arr.astype(np.int16).astype(np.float32)) / 32768.0
                            if self._recording_sample_rate is None:
                                self._recording_sample_rate = self._model_sr
                            # If passthrough mode (global) OR denoise disabled, send frames directly without chunking/overlap
                            if getattr(settings, 'AUDIO_PASSTHROUGH_ONLY', False) or not self.denoise_enabled:
                                self._recording_frames.append(mono.copy())
                                dead = []
                                for lid, q in self.listener_queues.items():
                                    try:
                                        if q.qsize() < 50:
                                            q.put_nowait((mono.copy(), self._model_sr))
                                    except Exception:
                                        dead.append(lid)
                                for lid in dead:
                                    self.listener_queues.pop(lid, None)
                            else:
                                pending = np.concatenate([pending, mono])

                        # Process as many full chunks as possible
                        while getattr(settings, 'AUDIO_PASSTHROUGH_ONLY', False) is False and self.denoise_enabled and pending.shape[0] >= self._chunk_frames:
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

                            # Overlap-add, streaming-safe:
                            # - Only output crossfaded head + non-overlapped middle
                            # - Withhold last overlap as prev_tail for next iteration
                            segments: list[torch.Tensor] = []
                            if self._overlap_frames > 0 and self._ramp_up is not None:
                                total = enhanced.shape[-1]
                                ov = min(self._overlap_frames, total)
                                if prev_tail is not None and ov > 0:
                                    head = enhanced[:, :ov]
                                    # crossfade overlapped portion with previous tail
                                    ramp_up = self._ramp_up if ov == self._overlap_frames else torch.linspace(0.0, 1.0, ov)
                                    ramp_down = self._ramp_down if ov == self._overlap_frames else torch.linspace(1.0, 0.0, ov)
                                    cf = prev_tail[:, -ov:] * ramp_down + head * ramp_up
                                    segments.append(cf)
                                else:
                                    # First chunk: do not output the last overlap; output up to total - ov
                                    pass

                                # Middle (non-overlapped) region: from ov to total - self._overlap_frames
                                mid_end = max(ov, total - self._overlap_frames)
                                if mid_end > ov:
                                    segments.append(enhanced[:, ov:mid_end])

                                # Set new tail as the last overlap region of current chunk (withhold from output now)
                                prev_tail = enhanced[:, -ov:] if ov > 0 else None
                            else:
                                # No overlap: output entire enhanced chunk
                                segments.append(enhanced)
                                prev_tail = None

                            # Fan out each denoised segment to all current listeners immediately
                            for seg in segments:
                                if seg.numel() == 0:
                                    continue
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

                # Flush any remaining audio as a final chunk
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

                        if self._overlap_frames and self._overlap_frames > 0 and enhanced.numel() > 0:
                            total = enhanced.shape[-1]
                            ov = min(self._overlap_frames, total)
                            if prev_tail is not None and ov > 0:
                                head = enhanced[:, :ov]
                                ramp_up = self._ramp_up if ov == self._overlap_frames else torch.linspace(0.0, 1.0, ov)
                                ramp_down = self._ramp_down if ov == self._overlap_frames else torch.linspace(1.0, 0.0, ov)
                                cf = prev_tail[:, -ov:] * ramp_down + head * ramp_up
                                self._recording_frames.append(cf.squeeze(0).numpy().astype(np.float32).copy())
                                # After crossfade at flush, output the remainder AND the last tail since no next chunk will come
                                remainder = enhanced[:, ov:]
                                if remainder.numel() > 0:
                                    self._recording_frames.append(remainder.squeeze(0).numpy().astype(np.float32).copy())
                            else:
                                # No prev tail: just output everything
                                self._recording_frames.append(enhanced.squeeze(0).numpy().astype(np.float32).copy())
                            # Also output the final tail since stream ends
                            if ov > 0:
                                tail = enhanced[:, -ov:]
                                self._recording_frames.append(tail.squeeze(0).numpy().astype(np.float32).copy())
                        else:
                            self._recording_frames.append(enhanced.squeeze(0).numpy().astype(np.float32).copy())
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
        # Reuse opus SDP munge to favor higher quality from browser sender
        def _munge_opus_sdp(sdp: str) -> str:
            try:
                lines = sdp.split('\r\n')
                opus_pt = None
                for line in lines:
                    if line.startswith('a=rtpmap:') and 'opus/48000' in line.lower():
                        try:
                            opus_pt = line.split(':', 1)[1].split(' ', 1)[0]
                            break
                        except Exception:
                            pass
                if not opus_pt:
                    return sdp
                fmtp_prefix = f'a=fmtp:{opus_pt} '
                found = False
                for i, line in enumerate(lines):
                    if line.startswith(fmtp_prefix):
                        found = True
                        params = line[len(fmtp_prefix):]
                        parts = [p for p in params.split(';') if p]
                        kv = {}
                        for p in parts:
                            if '=' in p:
                                k, v = p.split('=', 1)
                                kv[k.strip()] = v.strip()
                        kv.update({
                            'stereo': '0',
                            'sprop-stereo': '0',
                            'maxaveragebitrate': '192000',
                            'cbr': '1',
                            'useinbandfec': '1',
                            'ptime': '20',
                            'minptime': '10',
                        })
                        new_params = ';'.join([f"{k}={v}" for k, v in kv.items()])
                        lines[i] = fmtp_prefix + new_params
                        break
                if not found:
                    lines.append(
                        fmtp_prefix + 'stereo=0;sprop-stereo=0;maxaveragebitrate=192000;cbr=1;useinbandfec=1;ptime=20;minptime=10'
                    )
                return '\r\n'.join(lines)
            except Exception:
                return sdp

        munged = _munge_opus_sdp(answer.sdp)
        await self.pc.setLocalDescription(RTCSessionDescription(sdp=munged, type='answer'))
        return self.pc.localDescription.sdp

    async def create_listener_connection(self, listener_id: str, offer_sdp: str) -> str:
        from aiortc import RTCPeerConnection, RTCSessionDescription  # type: ignore

        try:
            await asyncio.wait_for(self.ready.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            raise Exception("Stream not yet ready (no audio track received)")

        listener_pc = RTCPeerConnection()
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
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
        # Munge Opus parameters in the SDP answer to improve quality
        def _munge_opus_sdp(sdp: str) -> str:
            try:
                lines = sdp.split('\r\n')
                opus_pt = None
                for line in lines:
                    if line.startswith('a=rtpmap:') and 'opus/48000' in line.lower():
                        try:
                            opus_pt = line.split(':', 1)[1].split(' ', 1)[0]
                            break
                        except Exception:
                            pass
                if not opus_pt:
                    return sdp
                fmtp_prefix = f'a=fmtp:{opus_pt} '
                found = False
                for i, line in enumerate(lines):
                    if line.startswith(fmtp_prefix):
                        found = True
                        params = line[len(fmtp_prefix):]
                        # Convert key=value; pairs to dict
                        parts = [p for p in params.split(';') if p]
                        kv = {}
                        for p in parts:
                            if '=' in p:
                                k, v = p.split('=', 1)
                                kv[k.strip()] = v.strip()
                        kv.update({
                            'stereo': '0',
                            'sprop-stereo': '0',
                            'maxaveragebitrate': '192000',
                            'cbr': '1',
                            'useinbandfec': '1',
                            'ptime': '20',
                            'minptime': '10',
                        })
                        new_params = ';'.join([f"{k}={v}" for k, v in kv.items()])
                        lines[i] = fmtp_prefix + new_params
                        break
                if not found:
                    lines.append(
                        fmtp_prefix + 'stereo=0;sprop-stereo=0;maxaveragebitrate=192000;cbr=1;useinbandfec=1;ptime=20;minptime=10'
                    )
                return '\r\n'.join(lines)
            except Exception:
                return sdp

        munged_sdp = _munge_opus_sdp(answer.sdp)
        await listener_pc.setLocalDescription(RTCSessionDescription(sdp=munged_sdp, type='answer'))
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
            # Clip to valid float range before writing
            np.clip(full_audio, -1.0, 1.0, out=full_audio)
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
