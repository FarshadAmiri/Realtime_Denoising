"""
Voice Enrollment System
Builds a database of speaker embeddings from reference audio samples
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from resemblyzer import VoiceEncoder, preprocess_wav
import torch
import torchaudio


class VoiceEnrollment:
    """
    Manages speaker enrollment and embedding database
    """
    
    def __init__(self, database_path: str):
        """
        Initialize voice enrollment system
        
        Args:
            database_path: Path to save/load speaker embeddings database
        """
        self.database_path = Path(database_path)
        self.encoder = VoiceEncoder()
        self.speaker_embeddings = {}
        
        # Load existing database if available
        if self.database_path.exists():
            self.load_database()
    
    def enroll_speaker(self, speaker_name: str, audio_path: str) -> np.ndarray:
        """
        Enroll a new speaker from reference audio
        
        Args:
            speaker_name: Unique identifier for the speaker
            audio_path: Path to reference audio file
            
        Returns:
            Speaker embedding vector
        """
        # Load and preprocess audio
        wav = preprocess_wav(audio_path)
        
        # Extract speaker embedding
        embedding = self.encoder.embed_utterance(wav)
        
        # Store in database
        self.speaker_embeddings[speaker_name] = embedding
        
        print(f"✓ Enrolled speaker: {speaker_name}")
        return embedding
    
    def enroll_multiple_samples(self, speaker_name: str, audio_paths: List[str]) -> np.ndarray:
        """
        Enroll speaker from multiple audio samples and average embeddings
        
        Args:
            speaker_name: Unique identifier for the speaker
            audio_paths: List of paths to reference audio files
            
        Returns:
            Averaged speaker embedding vector
        """
        embeddings = []
        
        for audio_path in audio_paths:
            wav = preprocess_wav(audio_path)
            embedding = self.encoder.embed_utterance(wav)
            embeddings.append(embedding)
        
        # Average embeddings for better representation
        avg_embedding = np.mean(embeddings, axis=0)
        
        # Normalize
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        
        # Store in database
        self.speaker_embeddings[speaker_name] = avg_embedding
        
        print(f"✓ Enrolled speaker: {speaker_name} (from {len(audio_paths)} samples)")
        return avg_embedding
    
    def save_database(self):
        """Save speaker embeddings to disk"""
        # Convert numpy arrays to lists for JSON serialization
        serializable_data = {
            name: embedding.tolist() 
            for name, embedding in self.speaker_embeddings.items()
        }
        
        with open(self.database_path, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        
        print(f"✓ Database saved to: {self.database_path}")
    
    def load_database(self):
        """Load speaker embeddings from disk"""
        with open(self.database_path, 'r') as f:
            data = json.load(f)
        
        # Convert lists back to numpy arrays
        self.speaker_embeddings = {
            name: np.array(embedding) 
            for name, embedding in data.items()
        }
        
        print(f"✓ Loaded {len(self.speaker_embeddings)} speakers from database")
    
    def identify_speaker(self, embedding: np.ndarray, threshold: float = 0.75) -> Optional[str]:
        """
        Identify speaker from embedding using cosine similarity
        
        Args:
            embedding: Speaker embedding to identify
            threshold: Minimum similarity score for positive identification
            
        Returns:
            Speaker name if identified, None otherwise
        """
        if not self.speaker_embeddings:
            return None
        
        best_match = None
        best_score = -1
        
        # Normalize query embedding
        embedding = embedding / np.linalg.norm(embedding)
        
        # Compare with all enrolled speakers
        for name, stored_embedding in self.speaker_embeddings.items():
            # Cosine similarity
            score = np.dot(embedding, stored_embedding)
            
            if score > best_score:
                best_score = score
                best_match = name
        
        # Return match only if above threshold
        if best_score >= threshold:
            return best_match
        
        return None
    
    def get_all_speakers(self) -> List[str]:
        """Get list of all enrolled speakers"""
        return list(self.speaker_embeddings.keys())
    
    def remove_speaker(self, speaker_name: str):
        """Remove a speaker from the database"""
        if speaker_name in self.speaker_embeddings:
            del self.speaker_embeddings[speaker_name]
            print(f"✓ Removed speaker: {speaker_name}")
        else:
            print(f"⚠ Speaker not found: {speaker_name}")


def create_voice_database(
    database_path: str,
    speaker_samples: Dict[str, List[str]]
) -> VoiceEnrollment:
    """
    Convenience function to create a voice database from speaker samples
    
    Args:
        database_path: Path to save the database
        speaker_samples: Dict mapping speaker names to lists of audio file paths
        
    Example:
        speaker_samples = {
            "John": ["john_sample1.wav", "john_sample2.wav"],
            "Jane": ["jane_sample1.wav"]
        }
    
    Returns:
        VoiceEnrollment object with enrolled speakers
    """
    enrollment = VoiceEnrollment(database_path)
    
    for speaker_name, audio_paths in speaker_samples.items():
        if len(audio_paths) == 1:
            enrollment.enroll_speaker(speaker_name, audio_paths[0])
        else:
            enrollment.enroll_multiple_samples(speaker_name, audio_paths)
    
    enrollment.save_database()
    
    return enrollment
