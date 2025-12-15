"""
Diarization Processor
Uses pyannote.audio for speaker diarization (detecting "who spoke when")
pyannote is production-ready, accurate, and compatible with existing dependencies
"""

import os
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json


class DiarizationProcessor:
    """
    Performs speaker diarization using pyannote.audio
    """
    
    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        """
        Initialize pyannote diarization processor
        
        Args:
            device: Device to run models on ('cuda' or 'cpu')
        """
        self.device = device
        print(f"Using device: {self.device}")
        
        # Import pyannote
        try:
            from pyannote.audio import Pipeline
            self.Pipeline = Pipeline
            print("✓ pyannote.audio imported successfully")
        except ImportError:
            raise ImportError(
                "pyannote.audio not installed. Please install with:\n"
                "pip install pyannote.audio"
            )
        
        self.pipeline = None
    
    def perform_diarization(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        window_size: float = 1.5,
        hop_size: float = 0.5
    ) -> List[Dict]:
        """
        Perform complete diarization on audio file using pyannote
        
        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (optional)
            window_size: Not used in pyannote (kept for API compatibility)
            hop_size: Not used in pyannote (kept for API compatibility)
            
        Returns:
            List of diarization segments with speaker labels
        """
        print(f"Processing: {audio_path}")
        
        # Get audio duration
        audio_info = torchaudio.info(audio_path)
        audio_duration = audio_info.num_frames / audio_info.sample_rate
        print(f"Audio duration: {audio_duration:.2f}s")
        
        # Load HF token
        hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')
        if not hf_token:
            print("Warning: HF token not found. Trying without authentication...")
        
        # Initialize pipeline (download on first use)
        if self.pipeline is None:
            print("Loading pyannote diarization pipeline...")
            self.pipeline = self.Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token
            )
            if torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))
        
        # Run diarization
        print("Running diarization...")
        if num_speakers is not None:
            diarization = self.pipeline(audio_path, num_speakers=num_speakers)
        else:
            diarization = self.pipeline(audio_path)
        
        # Convert to our format
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker
            })
        
        # Ensure final segment reaches audio end
        if segments and segments[-1]['end'] < audio_duration - 0.1:
            segments[-1]['end'] = audio_duration
        
        print(f"✓ Found {len(set(s['speaker'] for s in segments))} speakers")
        print(f"✓ Generated {len(segments)} segments")
        
        return segments
    
    def identify_speakers_in_segments(
        self,
        audio_path: str,
        segments: List[Dict],
        voice_enrollment
    ) -> List[Dict]:
        """
        Identify enrolled speakers in diarization segments
        
        Args:
            audio_path: Path to audio file
            segments: Diarization segments from perform_diarization
            voice_enrollment: VoiceEnrollment instance
            
        Returns:
            Segments with identified speaker names
        """
        # Load audio
        waveform, sr = torchaudio.load(audio_path)
        
        identified_segments = []
        
        for seg in segments:
            # Extract segment audio
            start_sample = int(seg['start'] * sr)
            end_sample = int(seg['end'] * sr)
            
            # Extract segment audio
            segment_audio = waveform[:, start_sample:end_sample]
            
            # Save temporarily for identification
            import tempfile
            temp_path = os.path.join(tempfile.gettempdir(), "temp_segment.wav")
            torchaudio.save(temp_path, segment_audio, sr)
            
            # Identify speaker
            speaker_name, confidence = voice_enrollment.identify_speaker(temp_path)
            
            # Update segment
            identified_seg = seg.copy()
            if speaker_name != "Unknown":
                identified_seg['speaker'] = speaker_name
                identified_seg['identified'] = True
                identified_seg['confidence'] = confidence
            else:
                identified_seg['identified'] = False
                identified_seg['confidence'] = confidence
            
            identified_segments.append(identified_seg)
            
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return identified_segments
    
    def save_diarization_results(
        self,
        segments: List[Dict],
        output_path: str,
        format: str = "json"
    ):
        """
        Save diarization results to file
        
        Args:
            segments: List of diarization segments
            output_path: Path to save results
            format: Output format ('json' or 'rttm')
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            with open(output_path, 'w') as f:
                json.dump(segments, f, indent=2)
        elif format == "rttm":
            with open(output_path, 'w') as f:
                for seg in segments:
                    duration = seg['end'] - seg['start']
                    f.write(
                        f"SPEAKER audio 1 {seg['start']:.3f} {duration:.3f} "
                        f"<NA> <NA> {seg['speaker']} <NA> <NA>\n"
                    )
        
        print(f"✓ Results saved to: {output_path}")
