"""
Audio processing wrapper for real-time denoising using dfn2.py
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import sys
import os

# Add parent directory to path to import dfn2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DFN2Processor:
    """Async-friendly wrapper for dfn2 denoising model."""
    
    def __init__(self, max_workers=4):
        """Initialize the processor with model and executor."""
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.model = None
        self.df_state = None
        self.device = None
        self.model_sr = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the model (call once at startup)."""
        if self._initialized:
            return
        
        # Lazy import to avoid loading at Django startup
        import torch
        import numpy as np
        from dfn2 import _init_model, enhance
        from df import config as df_config
        
        # Store imports as instance variables
        self.torch = torch
        self.np = np
        self.enhance = enhance
        self.df_config = df_config
        
        bundle = _init_model(force=False)
        self.model = bundle.model
        self.df_state = bundle.df_state
        self.device = bundle.device
        self.model_sr = df_config("sr", 48000, int, section="df")
        self._initialized = True
    
    async def process_frame(self, audio_frame):
        """
        Process a single audio frame asynchronously.
        
        Args:
            audio_frame: numpy array of audio samples (mono, float32)
        
        Returns:
            Denoised audio frame as numpy array
        """
        if not self._initialized:
            self.initialize()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._process_frame_sync,
            audio_frame
        )
    
    def _process_frame_sync(self, audio_frame):
        """
        Synchronous processing of audio frame (runs in thread pool).
        
        Args:
            audio_frame: numpy array of audio samples
        
        Returns:
            Denoised audio frame
        """
        # Convert to torch tensor
        if audio_frame.dtype != self.np.float32:
            audio_frame = audio_frame.astype(self.np.float32)
        
        # Ensure correct shape [1, samples]
        if audio_frame.ndim == 1:
            audio_tensor = self.torch.from_numpy(audio_frame).unsqueeze(0)
        else:
            audio_tensor = self.torch.from_numpy(audio_frame)
        
        # Process with model
        with self.torch.inference_mode():
            enhanced = self.enhance(self.model, self.df_state, audio_tensor).cpu()
        
        # Convert back to numpy
        enhanced_np = enhanced.squeeze(0).numpy()
        
        return enhanced_np
    
    async def process_frames_batch(self, frames: list) -> list:
        """
        Process multiple frames in batch for better efficiency.
        
        Args:
            frames: list of numpy arrays
        
        Returns:
            list of denoised numpy arrays
        """
        if not self._initialized:
            self.initialize()
        
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                self.executor,
                self._process_frame_sync,
                frame
            )
            for frame in frames
        ]
        
        return await asyncio.gather(*tasks)
    
    def shutdown(self):
        """Shutdown the executor."""
        self.executor.shutdown(wait=True)


# Global processor instance
_PROCESSOR: Optional[DFN2Processor] = None


def get_processor() -> DFN2Processor:
    """Get or create global processor instance."""
    global _PROCESSOR
    if _PROCESSOR is None:
        _PROCESSOR = DFN2Processor()
    return _PROCESSOR
