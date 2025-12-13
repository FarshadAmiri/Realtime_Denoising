"""
Diarization Processor
Uses NVIDIA NeMo for speaker diarization (detecting "who spoke when")
"""

import os
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
from omegaconf import OmegaConf
import tempfile
import shutil


class DiarizationProcessor:
    """
    Performs speaker diarization using NVIDIA NeMo
    """
    
    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        """
        Initialize NeMo diarization processor
        
        Args:
            device: Device to run models on ('cuda' or 'cpu')
        """
        self.device = device
        print(f"Using device: {self.device}")
        
        # Import NeMo modules
        try:
            from nemo.collections.asr.models import ClusteringDiarizer
            self.ClusteringDiarizer = ClusteringDiarizer
            print("✓ NeMo ASR imported successfully")
        except ImportError:
            raise ImportError(
                "NVIDIA NeMo not installed. Please install with:\n"
                "pip install nemo_toolkit[asr]"
            )
        
        self.diarizer = None
                run_opts={"device": device}
            )
        except Exception as e:
            print(f"Warning: Could not load SpeechBrain model: {e}")
            print("Continuing with Resemblyzer only...")
            self.speaker_model = None
        
        # Load Resemblyzer for embeddings
        self.encoder = VoiceEncoder(device=device)
        
        print("✓ Models loaded successfully")
    
    def extract_speaker_embeddings(
        self,
        audio_path: str,
        window_size: float = 1.5,
        hop_size: float = 0.75
    ) -> Tuple[List[np.ndarray], List[float]]:
        """
        Extract speaker embeddings from audio using sliding window
        
        Args:
            audio_path: Path to audio file
            window_size: Size of analysis window in seconds
            hop_size: Hop size between windows in seconds
            
        Returns:
            Tuple of (embeddings list, timestamps list)
        """
        # Get TRUE audio duration from original file
        audio_info = torchaudio.info(audio_path)
        audio_duration = audio_info.num_frames / audio_info.sample_rate
        
        # Load and resample audio for processing
        wav = preprocess_wav(audio_path)
        sample_rate = 16000  # Resemblyzer uses 16kHz
        
        # Calculate window parameters
        window_samples = int(window_size * sample_rate)
        hop_samples = int(hop_size * sample_rate)
        
        embeddings = []
        timestamps = []
        
        # Slide window through audio - process entire file
        start = 0
        while start < len(wav):
            end = min(start + window_samples, len(wav))
            segment = wav[start:end]
            
            # Pad if needed at the end
            if len(segment) < window_samples:
                segment = np.pad(segment, (0, window_samples - len(segment)), mode='constant')
            
            # Extract embedding (don't skip silent segments to ensure full coverage)
            embedding = self.encoder.embed_utterance(segment)
            embeddings.append(embedding)
            
            # Use WINDOW CENTER for accurate boundary placement
            # This represents the temporal center of the audio in this window
            timestamp = (start + window_samples // 2) / sample_rate
            timestamps.append(timestamp)
            
            start += hop_samples
        
        return embeddings, timestamps, audio_duration
    
    def cluster_speakers(
        self,
        embeddings: List[np.ndarray],
        timestamps: List[float],
        num_speakers: Optional[int] = None,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Cluster embeddings into speakers using agglomerative clustering
        
        Args:
            embeddings: List of speaker embeddings
            timestamps: Corresponding timestamps
            num_speakers: Number of speakers (if known), otherwise auto-detect
            threshold: Similarity threshold for clustering
            
        Returns:
            List of segments with speaker labels
        """
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Convert to numpy array
        X = np.array(embeddings)
        
        # Compute similarity matrix
        similarity = cosine_similarity(X)
        distance = 1 - similarity
        
        # Cluster
        if num_speakers:
            clustering = AgglomerativeClustering(
                n_clusters=num_speakers,
                metric='precomputed',
                linkage='average'
            )
        else:
            clustering = AgglomerativeClustering(
                n_clusters=None,
                metric='precomputed',
                linkage='average',
                distance_threshold=1 - threshold
            )
        
        labels = clustering.fit_predict(distance)
        
        # Create segments with boundaries at the midpoint between window centers
        segments = []
        current_speaker = None
        segment_start = None
        
        for i, (timestamp, label) in enumerate(zip(timestamps, labels)):
            speaker_id = f"Speaker_{label}"
            
            if speaker_id != current_speaker:
                # End previous segment at midpoint between consecutive window centers
                if current_speaker is not None:
                    segments.append({
                        'start': segment_start,
                        'end': timestamp,
                        'speaker': current_speaker
                    })
                
                # Start new segment
                current_speaker = speaker_id
                segment_start = timestamp

        # Add final segment - will be updated with actual duration later
        if current_speaker is not None:
            final_time = timestamps[-1] if len(timestamps) > 0 else segment_start
            segments.append({
                'start': segment_start,
                'end': final_time,
                'speaker': current_speaker
            })
        
        # Merge only consecutive segments from the SAME speaker
        segments = self._merge_segments(segments, min_gap=0.1)
        
        return segments
    
    def _merge_segments(self, segments: List[Dict], min_gap: float = 0.1) -> List[Dict]:
        """Merge adjacent segments from the same speaker"""
        if not segments:
            return []
        
        merged = [segments[0]]
        
        for seg in segments[1:]:
            prev = merged[-1]
            
            # ONLY merge if SAME speaker and very close (< min_gap)
            # This prevents merging different speakers but reduces fragmentation
            if seg['speaker'] == prev['speaker'] and seg['start'] - prev['end'] < min_gap:
                prev['end'] = seg['end']
            else:
                merged.append(seg)
        
        return merged
    
    def perform_diarization(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        window_size: float = 1.5,
        hop_size: float = 0.75
    ) -> List[Dict]:
        """
        Perform complete diarization on audio file
        
        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (optional)
            window_size: Analysis window size in seconds
            hop_size: Hop size in seconds
            
        Returns:
            List of diarization segments with speaker labels
        """
        print(f"Processing: {audio_path}")
        
        # Extract embeddings
        print("Extracting speaker embeddings...")
        embeddings, timestamps, audio_duration = self.extract_speaker_embeddings(
            audio_path, window_size, hop_size
        )
        
        print(f"Extracted {len(embeddings)} embeddings")
        print(f"Audio duration: {audio_duration:.2f}s")
        
        # Cluster speakers
        print("Clustering speakers...")
        segments = self.cluster_speakers(
            embeddings, timestamps, num_speakers
        )
        
        # Update final segment end time to match audio duration
        if segments and len(segments) > 0:
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
        Identify speakers in diarization segments using enrollment database
        
        Args:
            audio_path: Path to audio file
            segments: Diarization segments
            voice_enrollment: VoiceEnrollment object with speaker database
            
        Returns:
            Segments with identified speaker names
        """
        # Load audio
        waveform, sr = torchaudio.load(audio_path)
        
        # Process each segment
        for segment in segments:
            start_sample = int(segment['start'] * sr)
            end_sample = int(segment['end'] * sr)
            
            # Extract segment audio
            segment_audio = waveform[:, start_sample:end_sample]
            
            # Save temporarily
            temp_path = "temp_segment.wav"
            torchaudio.save(temp_path, segment_audio, sr)
            
            # Extract embedding
            wav = preprocess_wav(temp_path)
            embedding = self.encoder.embed_utterance(wav)
            
            # Identify speaker
            speaker_name = voice_enrollment.identify_speaker(embedding)
            
            if speaker_name:
                segment['speaker'] = speaker_name
                segment['identified'] = True
            else:
                segment['identified'] = False
            
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return segments
    
    def save_diarization_results(
        self,
        segments: List[Dict],
        output_path: str,
        format: str = "json"
    ):
        """
        Save diarization results to file
        
        Args:
            segments: Diarization segments
            output_path: Output file path
            format: Output format ('json', 'rttm', or 'txt')
        """
        if format == "json":
            with open(output_path, 'w') as f:
                json.dump(segments, f, indent=2)
        
        elif format == "rttm":
            # RTTM format for diarization evaluation
            with open(output_path, 'w') as f:
                for seg in segments:
                    duration = seg['end'] - seg['start']
                    f.write(f"SPEAKER <NA> 1 {seg['start']:.3f} {duration:.3f} "
                           f"<NA> <NA> {seg['speaker']} <NA> <NA>\n")
        
        elif format == "txt":
            with open(output_path, 'w') as f:
                for seg in segments:
                    f.write(f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['speaker']}\n")
        
        print(f"✓ Results saved to: {output_path}")
