
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Union
import torch
from loguru import logger
from df import config as df_config
from df.enhance import enhance, init_df, load_audio, save_audio
from df.io import resample

MODEL_DIR = Path("./DeepFilterNet2")


@dataclass
class _ModelBundle:
    model: torch.nn.Module
    df_state: object  # internal DeepFilterNet state object
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
    start_time = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
    if start_time is not None:
        start_time.record()

    ramp_up = None
    ramp_down = None
    if overlap_frames > 0:
        ramp_up = torch.linspace(0.0, 1.0, overlap_frames)
        ramp_down = torch.linspace(1.0, 0.0, overlap_frames)

    previous_tail = None  # Tensor of shape [1, overlap_frames]

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

    # Main capture loop
    elapsed = 0.0
    try:
        while True:
            if streaming_duration is not None and elapsed >= streaming_duration:
                break
            # Record one chunk (blocking)
            rec = sd.rec(frames=chunk_frames, samplerate=model_sr, channels=1, dtype="float32")
            sd.wait()
            raw = torch.from_numpy(rec.squeeze())  # shape [T]

            enhanced_chunk = _process_chunk(raw)

            # Crossfade with previous tail if requested
            if previous_tail is not None and overlap_frames > 0:
                head = enhanced_chunk[:, :overlap_frames]
                cf = previous_tail * ramp_down + head * ramp_up  # shape [1, overlap_frames]
                # Replace the last segment's tail: we appended full previous tail already; so append crossfaded portion + remainder
                # To avoid duplication, we drop the last overlap_frames from the previous appended segment
                if enhanced_segments:
                    enhanced_segments[-1] = torch.cat(
                        [enhanced_segments[-1][:, :-overlap_frames], cf], dim=1
                    )
                # Append remainder after head
                remainder = enhanced_chunk[:, overlap_frames:]
                if remainder.numel() > 0:
                    enhanced_segments.append(remainder)
                play_chunk = torch.cat([cf, remainder], dim=1)
            else:
                enhanced_segments.append(enhanced_chunk)
                play_chunk = enhanced_chunk

            previous_tail = enhanced_chunk[:, -overlap_frames:] if overlap_frames > 0 else None

            _play(play_chunk)

            elapsed += chunk_seconds
            total_captured = elapsed
    except KeyboardInterrupt:  # pragma: no cover
        logger.info("Streaming interrupted by user; finalizing...")

    # Concatenate all segments
    if not enhanced_segments:
        raise RuntimeError("No audio captured in streaming mode")
    final_enhanced = torch.cat(enhanced_segments, dim=1)

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
        "chunks": len(enhanced_segments),
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
