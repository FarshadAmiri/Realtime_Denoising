"""
Diarization Processor
Uses SpeechBrain for speaker diarization (detecting "who spoke when")
"""

import os
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from resemblyzer import VoiceEncoder, preprocess_wav
from speechbrain.pretrained import SpeakerRecognition, EncoderClassifier
import json


class DiarizationProcessor:
    """
    Performs speaker diarization using SpeechBrain
    """
    
    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        """
        Initialize diarization processor
        
        Args:
            device: Device to run models on ('cuda' or 'cpu')
        """
        self.device = device
        print(f"Using device: {self.device}")
        
        # Set up HuggingFace token if available
        hf_token_path = Path("hf_token.txt")
        if hf_token_path.exists():
            with open(hf_token_path, 'r') as f:
                token = f.read().strip()
                os.environ['HF_TOKEN'] = token
                os.environ['HUGGING_FACE_HUB_TOKEN'] = token
        
        # Load SpeechBrain speaker recognition model
        print("Loading SpeechBrain models...")
        try:
            self.speaker_model = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="Nemo-diarization/models/spkrec-ecapa-voxceleb",
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
        # Load audio
        wav = preprocess_wav(audio_path)
        sample_rate = 16000  # Resemblyzer uses 16kHz
        
        # Calculate window parameters
        window_samples = int(window_size * sample_rate)
        hop_samples = int(hop_size * sample_rate)
        
        embeddings = []
        timestamps = []
        
        # Slide window through audio
        for start in range(0, len(wav) - window_samples, hop_samples):
            end = start + window_samples
            segment = wav[start:end]
            
            # Skip silent segments
            if np.std(segment) < 0.01:
                continue
            
            # Extract embedding
            embedding = self.encoder.embed_utterance(segment)
            embeddings.append(embedding)
            
            # Calculate timestamp (center of window)
            timestamp = (start + window_samples // 2) / sample_rate
            timestamps.append(timestamp)
        
        return embeddings, timestamps
    
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
        
        # Create segments
        segments = []
        current_speaker = None
        segment_start = None
        
        for i, (timestamp, label) in enumerate(zip(timestamps, labels)):
            speaker_id = f"Speaker_{label}"
            
            if speaker_id != current_speaker:
                # End previous segment
                if current_speaker is not None:
                    segments.append({
                        'start': segment_start,
                        'end': timestamp,
                        'speaker': current_speaker
                    })
                
                # Start new segment
                current_speaker = speaker_id
                segment_start = timestamp
        
        # Add final segment
        if current_speaker is not None:
            segments.append({
                'start': segment_start,
                'end': timestamps[-1],
                'speaker': current_speaker
            })
        
        # Merge adjacent segments with same speaker
        segments = self._merge_segments(segments)
        
        return segments
    
    def _merge_segments(self, segments: List[Dict]) -> List[Dict]:
        """Merge adjacent segments from the same speaker"""
        if not segments:
            return []
        
        merged = [segments[0]]
        
        for seg in segments[1:]:
            prev = merged[-1]
            
            # Merge if same speaker and close in time
            if seg['speaker'] == prev['speaker'] and seg['start'] - prev['end'] < 0.5:
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
        embeddings, timestamps = self.extract_speaker_embeddings(
            audio_path, window_size, hop_size
        )
        
        print(f"Extracted {len(embeddings)} embeddings")
        
        # Cluster speakers
        print("Clustering speakers...")
        segments = self.cluster_speakers(
            embeddings, timestamps, num_speakers
        )
        
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
