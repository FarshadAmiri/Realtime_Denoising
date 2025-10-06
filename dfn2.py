
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Union
from queue import Empty, Full, Queue

import numpy as np
import torch
from loguru import logger

from df import config as df_config
from df.enhance import enhance, init_df, load_audio, save_audio
from df.io import resample

MODEL_DIR = Path("./DeepFilterNet2")


@dataclass
class _ModelBundle:
    model: torch.nn.Module
    df_state: object  # internal DeepFi-terNet state object
    device: torch.device


_MODEL_BUNDLE: Optional[_ModelBundle] = None


def _init_model(force: bool = False) -> _ModelBundle:
    """Initialize and cache the DeepFilterNet2 model."""
    global _MODEL_BUNDLE
    if _MODEL_BUNDLE is not None and not force:
        return _MODEL_BUNDLE
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, df_state, _ = init_df(str(MODEL_DIR), config_allow_defaults=True)
    model = model.to(device=device).eval()
    logger.info(f"DeepFilterNet2 model initialized on device {device}")
    _MODEL_BUNDLE = _ModelBundle(model=model, df_state=df_state, device=device)
    return _MODEL_BUNDLE


def denoise_file(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    max_seconds: Optional[int] = None,
    fade_in_seconds: float = 0.15,
    return_tensor: bool = False,
    force_reinit: bool = False,
) -> Dict[str, Union[str, int, torch.Tensor]]:
    """Denoise an audio file and save the enhanced result.

    Parameters
    ----------
    input_path : str | Path
        Path to the input audio file.
    output_path : str | Path
        Path where enhanced audio will be written (directories auto-created).
    max_seconds : int | None
        If set, truncate (random segment) to this many seconds before enhancement.
        If None, process the full file (may use more memory/time for long inputs).
    fade_in_seconds : float
        Linear fade-in applied at the start of enhanced signal to avoid pops.
    return_tensor : bool
        If True, include the enhanced tensor (at original sample rate) in the returned dict.
    force_reinit : bool
        If True, re-initialize the model (useful after checkpoint changes).

    Returns
    -------
    dict
        Keys: 'input_path', 'enhanced_path', 'original_sample_rate', 'model_sample_rate',
        and optionally 'tensor'.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input audio not found: {input_path}")

    bundle = _init_model(force=force_reinit)
    model = bundle.model
    df_state = bundle.df_state
    device = bundle.device

    model_sr = df_config("sr", 48000, int, section="df")
    audio, meta = load_audio(str(input_path), model_sr)  # audio now at model_sr
    original_sr = meta.sample_rate if meta.sample_rate > 0 else model_sr

    # Optional truncation
    if max_seconds is not None:
        max_len = int(max_seconds * model_sr)
        if audio.shape[-1] > max_len:
            start = torch.randint(0, audio.shape[-1] - max_len, ()).item()
            audio = audio[..., start : start + max_len]

    if audio.dim() > 1 and audio.shape[0] > 1:
        audio = audio.mean(dim=0, keepdim=True)

    # Use f-string; previous '%s' style wasn't interpolated by loguru
    logger.info(f"Enhancing file: {input_path}")
    # NOTE: Keep audio on CPU because df.enhance -> df_features calls .numpy() on it.
    # Moving it to CUDA causes: TypeError: can't convert cuda tensor to numpy.
    with torch.inference_mode():
        enhanced = enhance(model, df_state, audio).cpu()
    # Clone to obtain a normal tensor that allows safe post-processing (inplace ops disallowed on inference tensors)
    enhanced = enhanced.clone()

    # Fade-in
    fade_len = int(fade_in_seconds * model_sr)
    if 0 < fade_len < enhanced.shape[-1]:
        ramp = torch.linspace(0.0, 1.0, fade_len, device=enhanced.device).unsqueeze(0)
        # Apply fade without in-place modification on inference tensor reference
        enhanced = torch.cat([
            enhanced[:, :fade_len] * ramp,
            enhanced[:, fade_len:]
        ], dim=1)

    # Resample back if original sr differs
    if original_sr != model_sr:
        enhanced_out = resample(enhanced, model_sr, original_sr)
    else:
        enhanced_out = enhanced

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_audio(str(output_path), enhanced_out, original_sr)
    logger.info("Saved enhanced audio -> %s", output_path)

    result: Dict[str, Union[str, int, torch.Tensor]] = {
        "input_path": str(input_path),
        "enhanced_path": str(output_path),
        "original_sample_rate": original_sr,
        "model_sample_rate": model_sr,
    }
    if return_tensor:
        result["tensor"] = enhanced_out
    return result


__all__ = ["denoise_file"]

def denoise(
    input_mode: str,
    output_path: Union[str, Path],
    input_path: Optional[Union[str, Path]] = None,
    *,
    # File mode options
    max_seconds: Optional[int] = None,
    # Streaming mode options
    streaming_duration: Optional[int] = 30,  # total duration to capture (seconds); None = until KeyboardInterrupt
    chunk_seconds: float = 4.0,
    overlap_seconds: float = 0.25,
    playback: bool = True,
    playback_blocking: bool = True,
    # Common options
    fade_in_seconds: float = 0.15,
    return_tensor: bool = False,
    force_reinit: bool = False,
) -> Dict[str, Union[str, int, torch.Tensor]]:
    """Unified denoising entrypoint supporting 'file' and 'streaming' modes.

    Parameters
    ----------
    input_mode : str
        'file' or 'streaming'. In 'file' mode a disk file is enhanced. In
        'streaming' mode microphone audio is captured in chunks, enhanced, optionally
        played back, and finally written to `output_path` as a single file.
    output_path : str | Path
        Destination path for enhanced audio (file mode) or accumulated stream (streaming mode).
    input_path : str | Path | None
        Required in file mode; ignored in streaming mode.
    max_seconds : int | None
        (File mode) Optional truncation.
    streaming_duration : int | None
        (Streaming) Total seconds to run; None means run until Ctrl+C.
    chunk_seconds : float
        (Streaming) Capture & enhancement chunk length. Larger chunks increase latency
        but improve quality; user allows up to ~8s latency, default 4s.
    overlap_seconds : float
        (Streaming) Crossfade overlap between consecutive enhanced chunks.
    playback : bool
        (Streaming) Play enhanced audio chunks through default output device.
    playback_blocking : bool
        (Streaming) If True, playback waits for each chunk to finish before recording next chunk (simpler & reliable).
        If False, attempts non-blocking playback (may fail on some devices due to half-duplex limitations).
    fade_in_seconds : float
        Small fade-in applied per file (file mode) or per chunk (streaming) start.
    return_tensor : bool
        Return the final enhanced tensor (may consume memory for long streams).
    force_reinit : bool
        Re-initialize model (e.g. after replacing checkpoint).

    Returns
    -------
    dict with keys (file mode): see denoise_file
    dict with additional keys (streaming): 'chunks', 'stream_duration_seconds'
    """
    input_mode = input_mode.lower()
    if input_mode not in {"file", "streaming"}:
        raise ValueError("input_mode must be 'file' or 'streaming'")

    if input_mode == "file":
        if input_path is None:
            raise ValueError("input_path is required in file mode")
        return denoise_file(
            input_path=input_path,
            output_path=output_path,
            max_seconds=max_seconds,
            fade_in_seconds=fade_in_seconds,
            return_tensor=return_tensor,
            force_reinit=force_reinit,
        )

    # ---- Streaming Mode ----
    try:
        import sounddevice as sd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "Streaming mode requires the 'sounddevice' package. Install via 'pip install sounddevice'."
        ) from e

    bundle = _init_model(force=force_reinit)
    model = bundle.model
    df_state = bundle.df_state
    device = bundle.device  # currently unused but kept for parity

    model_sr = df_config("sr", 48000, int, section="df")

    if overlap_seconds < 0 or overlap_seconds >= chunk_seconds:
        overlap_seconds = 0.0

    chunk_frames = int(chunk_seconds * model_sr)
    overlap_frames = int(overlap_seconds * model_sr)
    fade_in_frames = int(fade_in_seconds * model_sr)

    logger.info(
        f"Starting streaming denoise: chunk={chunk_seconds:.2f}s overlap={overlap_seconds:.2f}s target_sr={model_sr}"
    )

    enhanced_segments = []  # list[Tensor]
    total_captured = 0.0

    ramp_up = None
    ramp_down = None
    if overlap_frames > 0:
        ramp_up = torch.linspace(0.0, 1.0, overlap_frames)
        ramp_down = torch.linspace(1.0, 0.0, overlap_frames)

    previous_tail = None  # Tensor of shape [1, overlap_frames]

    audio_queue: Queue[np.ndarray] = Queue(maxsize=8)
    stream_error: Optional[Exception] = None

    def _input_callback(indata, frames, time_info, status):  # pragma: no cover - callback
        nonlocal stream_error
        if status:
            logger.warning(f"Input stream status: {status}")
        try:
            audio_queue.put_nowait(indata[:, 0].copy())
        except Full:
            logger.warning("Input queue full; dropping chunk")
        except Exception as exc:  # pragma: no cover
            stream_error = exc

    def _next_chunk(timeout: float = 1.0) -> np.ndarray:
        while True:
            if stream_error is not None:
                raise stream_error
            try:
                return audio_queue.get(timeout=timeout)
            except Empty:
                continue

    def _process_chunk(raw_chunk: torch.Tensor) -> torch.Tensor:
        # raw_chunk shape [samples] or [1, samples]
        if raw_chunk.dim() == 1:
            raw_chunk_t = raw_chunk.unsqueeze(0)
        else:
            raw_chunk_t = raw_chunk
        # Ensure model sr (device capture may already be correct)
        # sounddevice provides float32 in [-1,1]
        with torch.inference_mode():
            enhanced_chunk = enhance(model, df_state, raw_chunk_t).cpu().clone()
        # Apply per-chunk fade-in only at very beginning of the whole stream
        nonlocal total_captured
        if total_captured == 0.0 and 0 < fade_in_frames < enhanced_chunk.shape[-1]:
            # Build new tensor to avoid in-place modification on inference tensor
            fade_ramp = torch.linspace(0.0, 1.0, fade_in_frames, device=enhanced_chunk.device).unsqueeze(0)
            enhanced_chunk = torch.cat([
                enhanced_chunk[:, :fade_in_frames] * fade_ramp,
                enhanced_chunk[:, fade_in_frames:]
            ], dim=1)
        # ensure we return a normal (non-inference) tensor for any later in-place safe ops
        enhanced_chunk = enhanced_chunk.clone()
        return enhanced_chunk

    play_stream = None
    if playback and not playback_blocking:
        # Try to create a persistent output stream for non-blocking playback
        try:
            play_stream = sd.OutputStream(samplerate=model_sr, channels=1, dtype="float32")
            play_stream.start()
        except Exception as pe:
            logger.warning(f"Falling back to blocking playback: could not open OutputStream ({pe})")
            play_stream = None
            playback_blocking = True

    def _play(t: torch.Tensor):  # playback helper
        if not playback:
            return
        data = t.squeeze(0).numpy()
        try:
            if playback_blocking:
                sd.play(data, samplerate=model_sr, blocking=True)
            else:
                if play_stream is not None:
                    play_stream.write(data)
                else:  # fallback just in case
                    sd.play(data, samplerate=model_sr, blocking=True)
        except Exception as pe:  # pragma: no cover
            logger.warning(f"Playback failed: {pe}")

    target_frames = int(streaming_duration * model_sr) if streaming_duration is not None else None
    total_output_frames = 0
    captured_frames = 0
    processed_chunks = 0

    try:
        with sd.InputStream(
            samplerate=model_sr,
            channels=1,
            dtype="float32",
            blocksize=chunk_frames,
            callback=_input_callback,
        ):
            while True:
                if target_frames is not None and captured_frames >= target_frames:
                    break

                chunk_np = _next_chunk()
                raw = torch.from_numpy(np.asarray(chunk_np, dtype=np.float32))  # shape [T]

                enhanced_chunk = _process_chunk(raw)

                captured_frames += raw.shape[-1]
                processed_chunks += 1

                # Crossfade with previous tail if requested
                if previous_tail is not None and overlap_frames > 0:
                    head = enhanced_chunk[:, :overlap_frames]
                    cf = previous_tail * ramp_down + head * ramp_up  # shape [1, overlap_frames]

                    enhanced_segments.append(cf)
                    total_output_frames += cf.shape[-1]

                    remainder = enhanced_chunk[:, overlap_frames:]
                    if remainder.numel() > 0:
                        enhanced_segments.append(remainder)
                        total_output_frames += remainder.shape[-1]

                    play_chunk = torch.cat([cf, remainder], dim=1)
                else:
                    enhanced_segments.append(enhanced_chunk)
                    total_output_frames += enhanced_chunk.shape[-1]
                    play_chunk = enhanced_chunk

                previous_tail = enhanced_chunk[:, -overlap_frames:] if overlap_frames > 0 else None

                total_captured = captured_frames / model_sr

                _play(play_chunk)
    except KeyboardInterrupt:  # pragma: no cover
        logger.info("Streaming interrupted by user; finalizing...")

    # Concatenate all segments
    if not enhanced_segments:
        raise RuntimeError("No audio captured in streaming mode")
    final_enhanced = torch.cat(enhanced_segments, dim=1)

    # Ensure output duration matches captured microphone frames
    if final_enhanced.shape[-1] > captured_frames > 0:
        final_enhanced = final_enhanced[:, :captured_frames]
        total_output_frames = captured_frames
    elif captured_frames > final_enhanced.shape[-1]:
        pad = captured_frames - final_enhanced.shape[-1]
        pad_values = final_enhanced[:, -1:].repeat(1, pad)
        final_enhanced = torch.cat([final_enhanced, pad_values], dim=1)
        total_output_frames = captured_frames
    else:
        total_output_frames = final_enhanced.shape[-1]

    total_captured = total_output_frames / model_sr

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_audio(str(output_path), final_enhanced, model_sr)
    logger.info(f"Saved streaming enhanced audio -> {output_path}")

    if playback and not playback_blocking:
        try:
            if play_stream is not None:
                play_stream.stop(); play_stream.close()
        except Exception:
            pass

    result: Dict[str, Union[str, int, torch.Tensor]] = {
        "input_path": "<microphone>",
        "enhanced_path": str(output_path),
        "original_sample_rate": model_sr,
        "model_sample_rate": model_sr,
        "stream_duration_seconds": int(total_captured),
        "chunks": processed_chunks,
    }
    if return_tensor:
        result["tensor"] = final_enhanced
    return result

__all__.append("denoise")

# ---------------------------------------------------------------------------
# Example Usage (Commented)
# ---------------------------------------------------------------------------
# These blocks are commented out so importing this module has no side effects.
# Uncomment the section you want to test.

# === Example 1: File Mode (single offline file) ===
# if __name__ == "__main__":
#     input_wav = r"C:\Users\User_1\Desktop\noisy_auido_files\noisy_fish.wav"  # replace with your path
#     output_wav = r"C:\\Users\\User_1\\Desktop\\output_file_mode.wav"
#     result = denoise(
#         input_mode="file",
#         input_path=input_wav,
#         output_path=output_wav,
#         max_seconds=None,            # or an int to truncate
#         fade_in_seconds=0.15,
#         return_tensor=False,
#     )
#     print("[FILE MODE] Enhanced file:", result["enhanced_path"], "SR:", result["original_sample_rate"])  


# === Example 2: Streaming Mode (microphone capture) ===
# if __name__ == "__main__":
#     output_stream_wav = r"C:\\Users\\User_1\\Desktop\\output_stream_mode.wav"
#     result_stream = denoise(
#         input_mode="streaming",
#         output_path=output_stream_wav,
#         streaming_duration=None,    # capture 20 seconds (None = until Ctrl+C)
#         chunk_seconds=6.0,        # larger chunk for better quality (higher latency)
#         overlap_seconds=0.5,      # smooth crossfade
#         playback=True,            # set False to disable live playback
#         fade_in_seconds=0.15,
#         return_tensor=False,
#     )
#     print("[STREAMING MODE] Enhanced file:", result_stream["enhanced_path"],
#           "Duration:", result_stream["stream_duration_seconds"], "s", "Chunks:", result_stream["chunks"]) 
