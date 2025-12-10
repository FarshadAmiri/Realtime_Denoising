"""
Transcription Integration
Combines Whisper transcription with diarization results
"""

import os
import torch
import whisper
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
import torchaudio


class TranscriptionProcessor:
    """
    Handles transcription using Whisper and alignment with diarization
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: str = "base",
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        """
        Initialize transcription processor
        
        Args:
            model_path: Path to custom Whisper model (optional)
            model_name: Whisper model name ('tiny', 'base', 'small', 'medium', 'large')
            device: Device to run on
        """
        self.device = device
        print(f"Loading Whisper model on {device}...")
        
        if model_path and os.path.exists(model_path):
            # Load custom model
            self.model = whisper.load_model(model_path, device=device)
            print(f"✓ Loaded custom model from: {model_path}")
        else:
            # Load standard model
            self.model = whisper.load_model(model_name, device=device)
            print(f"✓ Loaded Whisper {model_name} model")
    
    def transcribe_audio(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict:
        """
        Transcribe entire audio file
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'fa', 'ar') or None for auto-detect
            task: 'transcribe' or 'translate'
            
        Returns:
            Whisper transcription result with segments
        """
        print(f"Transcribing: {audio_path}")
        
        # Transcribe
        result = self.model.transcribe(
            audio_path,
            language=language,
            task=task,
            word_timestamps=True,
            verbose=False
        )
        
        print(f"✓ Transcription complete")
        print(f"  Detected language: {result.get('language', 'unknown')}")
        print(f"  Segments: {len(result.get('segments', []))}")
        
        return result
    
    def align_transcription_with_diarization(
        self,
        transcription_segments: List[Dict],
        diarization_segments: List[Dict]
    ) -> List[Dict]:
        """
        Align transcription segments with speaker diarization
        
        Args:
            transcription_segments: Whisper transcription segments
            diarization_segments: Speaker diarization segments
            
        Returns:
            Combined segments with speaker and text
        """
        combined = []
        
        for trans_seg in transcription_segments:
            trans_start = trans_seg['start']
            trans_end = trans_seg['end']
            trans_mid = (trans_start + trans_end) / 2
            
            # Find overlapping speaker
            speaker = self._find_speaker_at_time(trans_mid, diarization_segments)
            
            combined.append({
                'start': trans_start,
                'end': trans_end,
                'speaker': speaker,
                'text': trans_seg['text'].strip()
            })
        
        return combined
    
    def _find_speaker_at_time(
        self,
        timestamp: float,
        diarization_segments: List[Dict]
    ) -> str:
        """Find which speaker is active at given timestamp"""
        for seg in diarization_segments:
            if seg['start'] <= timestamp <= seg['end']:
                return seg['speaker']
        
        # Return closest speaker if not found
        closest = min(
            diarization_segments,
            key=lambda s: min(
                abs(s['start'] - timestamp),
                abs(s['end'] - timestamp)
            )
        )
        return closest['speaker']
    
    def merge_adjacent_segments(
        self,
        segments: List[Dict],
        max_gap: float = 2.0
    ) -> List[Dict]:
        """
        Merge adjacent segments from same speaker
        
        Args:
            segments: Combined diarization + transcription segments
            max_gap: Maximum gap in seconds to merge across
            
        Returns:
            Merged segments
        """
        if not segments:
            return []
        
        merged = [segments[0].copy()]
        
        for seg in segments[1:]:
            prev = merged[-1]
            
            # Merge if same speaker and within max_gap
            if (seg['speaker'] == prev['speaker'] and 
                seg['start'] - prev['end'] < max_gap):
                prev['end'] = seg['end']
                prev['text'] += ' ' + seg['text']
            else:
                merged.append(seg.copy())
        
        return merged
    
    def format_transcript(
        self,
        segments: List[Dict],
        format: str = "text"
    ) -> str:
        """
        Format transcript for output
        
        Args:
            segments: Combined segments
            format: 'text', 'srt', or 'vtt'
            
        Returns:
            Formatted transcript string
        """
        if format == "text":
            lines = []
            for seg in segments:
                lines.append(f"{seg['speaker']}: {seg['text']}")
            return '\n\n'.join(lines)
        
        elif format == "srt":
            lines = []
            for i, seg in enumerate(segments, 1):
                start = self._format_timestamp_srt(seg['start'])
                end = self._format_timestamp_srt(seg['end'])
                lines.append(f"{i}")
                lines.append(f"{start} --> {end}")
                lines.append(f"[{seg['speaker']}] {seg['text']}")
                lines.append("")
            return '\n'.join(lines)
        
        elif format == "vtt":
            lines = ["WEBVTT", ""]
            for seg in segments:
                start = self._format_timestamp_vtt(seg['start'])
                end = self._format_timestamp_vtt(seg['end'])
                lines.append(f"{start} --> {end}")
                lines.append(f"<v {seg['speaker']}>{seg['text']}")
                lines.append("")
            return '\n'.join(lines)
        
        return ""
    
    def _format_timestamp_srt(self, seconds: float) -> str:
        """Format timestamp for SRT format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_timestamp_vtt(self, seconds: float) -> str:
        """Format timestamp for WebVTT format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def save_transcript(
        self,
        segments: List[Dict],
        output_path: str,
        format: str = "text"
    ):
        """
        Save transcript to file
        
        Args:
            segments: Combined segments
            output_path: Output file path
            format: Output format ('text', 'srt', 'vtt', or 'json')
        """
        if format == "json":
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(segments, f, indent=2, ensure_ascii=False)
        else:
            transcript = self.format_transcript(segments, format)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transcript)
        
        print(f"✓ Transcript saved to: {output_path}")
