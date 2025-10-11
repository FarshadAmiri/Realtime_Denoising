"""
Audio processing service for real-time denoising integration with dfn2.py

This module provides a high-level interface for processing audio streams
with DeepFilterNet2 denoising in a WebRTC context.
"""

import io
import numpy as np
import torch
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
from django.conf import settings

# Import dfn2 denoising functions
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from dfn2 import _init_model, enhance
from df import config as df_config


class AudioProcessor:
    """
    Manages audio processing with DeepFilterNet2 denoising.
    
    Handles chunk buffering, denoising, crossfading, and recording.
    """
    
    def __init__(self, session_id: str, denoise_enabled: bool = True):
        """
        Initialize audio processor.
        
        Args:
            session_id: Unique session identifier
            denoise_enabled: Whether to apply denoising
        """
        self.session_id = session_id
        self.denoise_enabled = denoise_enabled
        self.sample_rate = getattr(settings, 'AUDIO_SAMPLE_RATE', 48000)
        self.chunk_seconds = getattr(settings, 'AUDIO_CHUNK_SECONDS', 2.0)
        self.overlap_seconds = getattr(settings, 'AUDIO_OVERLAP_SECONDS', 0.5)
        
        self.chunk_frames = int(self.chunk_seconds * self.sample_rate)
        self.overlap_frames = int(self.overlap_seconds * self.sample_rate)
        
        # Initialize model if denoising is enabled
        self.model = None
        self.df_state = None
        if self.denoise_enabled:
            self._init_denoising()
        
        # Buffers
        self.audio_buffer = []  # Accumulated raw audio
        self.processed_segments = []  # Denoised segments
        self.previous_tail = None  # For crossfading
        
        # Crossfade ramps
        if self.overlap_frames > 0:
            self.ramp_up = torch.linspace(0.0, 1.0, self.overlap_frames)
            self.ramp_down = torch.linspace(1.0, 0.0, self.overlap_frames)
        else:
            self.ramp_up = None
            self.ramp_down = None
        
        # Statistics
        self.total_frames = 0
        self.chunks_processed = 0
        self.started_at = datetime.now()
    
    def _init_denoising(self):
        """Initialize DeepFilterNet2 model."""
        try:
            bundle = _init_model(force=False)
            self.model = bundle.model
            self.df_state = bundle.df_state
            print(f"[AudioProcessor] Denoising model initialized for session {self.session_id}")
        except Exception as e:
            print(f"[AudioProcessor] Failed to initialize denoising model: {e}")
            self.denoise_enabled = False
    
    def process_audio_chunk(self, audio_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Process incoming audio chunk.
        
        Args:
            audio_data: Raw audio data (mono, float32, sample_rate)
        
        Returns:
            Processed audio chunk ready for streaming, or None if buffering
        """
        # Add to buffer
        self.audio_buffer.append(audio_data)
        self.total_frames += len(audio_data)
        
        # Check if we have enough frames for a chunk
        buffered_frames = sum(len(seg) for seg in self.audio_buffer)
        
        if buffered_frames < self.chunk_frames:
            return None  # Still buffering
        
        # Extract chunk
        chunk = np.concatenate(self.audio_buffer)[:self.chunk_frames]
        
        # Keep remaining in buffer
        remaining = np.concatenate(self.audio_buffer)[self.chunk_frames:]
        self.audio_buffer = [remaining] if len(remaining) > 0 else []
        
        # Process chunk
        if self.denoise_enabled and self.model is not None:
            processed = self._denoise_chunk(chunk)
        else:
            processed = chunk
        
        # Apply crossfade with previous tail
        if self.previous_tail is not None and self.overlap_frames > 0:
            output = self._apply_crossfade(processed)
        else:
            output = processed
        
        # Store tail for next crossfade
        if self.overlap_frames > 0:
            self.previous_tail = processed[-self.overlap_frames:]
        
        # Store in recording buffer
        self.processed_segments.append(output)
        
        self.chunks_processed += 1
        
        return output
    
    def _denoise_chunk(self, chunk: np.ndarray) -> np.ndarray:
        """
        Apply denoising to audio chunk.
        
        Args:
            chunk: Raw audio chunk
        
        Returns:
            Denoised audio chunk
        """
        try:
            # Convert to tensor
            audio_tensor = torch.from_numpy(chunk).float().unsqueeze(0)  # [1, samples]
            
            # Apply denoising
            with torch.inference_mode():
                enhanced = enhance(self.model, self.df_state, audio_tensor)
            
            # Convert back to numpy
            denoised = enhanced.squeeze(0).cpu().numpy()
            
            return denoised.astype(np.float32)
            
        except Exception as e:
            print(f"[AudioProcessor] Error during denoising: {e}")
            # Return original on error
            return chunk
    
    def _apply_crossfade(self, current_chunk: np.ndarray) -> np.ndarray:
        """
        Apply crossfade between previous tail and current chunk head.
        
        Args:
            current_chunk: Current processed chunk
        
        Returns:
            Chunk with crossfade applied
        """
        head = current_chunk[:self.overlap_frames]
        remainder = current_chunk[self.overlap_frames:]
        
        # Crossfade
        ramp_up_np = self.ramp_up.numpy()
        ramp_down_np = self.ramp_down.numpy()
        
        crossfaded = self.previous_tail * ramp_down_np + head * ramp_up_np
        
        # Concatenate crossfaded part with remainder
        output = np.concatenate([crossfaded, remainder])
        
        return output
    
    def finalize(self) -> Tuple[np.ndarray, float]:
        """
        Finalize recording and return complete audio.
        
        Returns:
            Tuple of (complete_audio, duration_seconds)
        """
        # Process any remaining buffered audio
        if len(self.audio_buffer) > 0:
            remaining = np.concatenate(self.audio_buffer)
            if len(remaining) > 0:
                if self.denoise_enabled and self.model is not None:
                    processed = self._denoise_chunk(remaining)
                else:
                    processed = remaining
                
                self.processed_segments.append(processed)
        
        # Concatenate all segments
        if len(self.processed_segments) > 0:
            complete_audio = np.concatenate(self.processed_segments)
        else:
            complete_audio = np.array([], dtype=np.float32)
        
        duration = len(complete_audio) / self.sample_rate
        
        return complete_audio, duration
    
    def get_stats(self) -> dict:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with processing stats
        """
        elapsed = (datetime.now() - self.started_at).total_seconds()
        
        return {
            'session_id': self.session_id,
            'denoise_enabled': self.denoise_enabled,
            'chunks_processed': self.chunks_processed,
            'total_frames': self.total_frames,
            'duration': self.total_frames / self.sample_rate,
            'elapsed_time': elapsed,
            'sample_rate': self.sample_rate,
        }


def save_recording_to_file(audio: np.ndarray, sample_rate: int, output_path: str):
    """
    Save audio recording to WAV file.
    
    Args:
        audio: Audio data (mono, float32)
        sample_rate: Sample rate
        output_path: Output file path
    """
    from df.io import save_audio
    import torch
    
    # Convert to tensor
    audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)  # [1, samples]
    
    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_audio(str(output_path), audio_tensor, sample_rate)
    
    print(f"[AudioProcessor] Saved recording to {output_path}")
