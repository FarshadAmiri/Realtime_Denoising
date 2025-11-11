import os
import torch
import torchaudio
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from spectralcluster import SpectralClusterer
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import SpeakerExtractionFile


def load_and_preprocess(audio_path):
    """Load audio file and preprocess for Resemblyzer."""
    waveform, sr = torchaudio.load(audio_path)
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)
    audio_np = waveform.squeeze().numpy()
    preprocessed = preprocess_wav(audio_np, source_sr=sr)
    return preprocessed, sr


def extract_speaker_segments(audio, encoder, window_sec=1.5, overlap=0.5):
    """Extract speaker embeddings from audio segments."""
    sr = 16000
    window_samples = int(window_sec * sr)
    hop_samples = int(window_samples * (1 - overlap))
    embeddings = []
    timestamps = []
    
    for start in range(0, len(audio) - window_samples, hop_samples):
        end = start + window_samples
        segment = audio[start:end]
        if len(segment) == window_samples:
            embedding = encoder.embed_utterance(segment)
            embeddings.append(embedding)
            timestamps.append((start / sr, end / sr))
    
    return np.array(embeddings), timestamps


def cluster_speakers(embeddings, n_speakers=2):
    """Cluster speaker embeddings."""
    clusterer = SpectralClusterer(
        min_clusters=n_speakers,
        max_clusters=n_speakers
    )
    labels = clusterer.predict(embeddings)
    return labels


def find_matching_speaker(target_embedding, conversation_embeddings, labels):
    """Find which cluster matches the target speaker best."""
    unique_labels = np.unique(labels)
    cluster_similarities = []
    
    for label in unique_labels:
        cluster_mask = labels == label
        cluster_embeddings = conversation_embeddings[cluster_mask]
        similarities = [
            np.dot(target_embedding, emb) / (np.linalg.norm(target_embedding) * np.linalg.norm(emb)) 
            for emb in cluster_embeddings
        ]
        avg_similarity = np.mean(similarities)
        cluster_similarities.append((label, avg_similarity))
    
    best_cluster = max(cluster_similarities, key=lambda x: x[1])
    return best_cluster[0], best_cluster[1]


def reconstruct_audio(audio, labels, timestamps, target_label):
    """Reconstruct audio with only the target speaker's segments."""
    sr = 16000
    output_audio = np.zeros_like(audio)
    
    for i, (start_time, end_time) in enumerate(timestamps):
        if labels[i] == target_label:
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            output_audio[start_sample:end_sample] = audio[start_sample:end_sample]
    
    return output_audio


def process_speaker_extraction(file_id):
    """Process speaker extraction for a given file ID."""
    try:
        extraction_file = SpeakerExtractionFile.objects.get(id=file_id)
        extraction_file.status = 'processing'
        extraction_file.save()
        
        # Initialize voice encoder
        encoder = VoiceEncoder()
        
        # Load target speaker sample
        target_audio, _ = load_and_preprocess(extraction_file.target_speaker_file.path)
        target_embedding = encoder.embed_utterance(target_audio)
        
        # Load conversation
        conversation_audio, _ = load_and_preprocess(extraction_file.conversation_file.path)
        
        # Extract speaker embeddings from conversation
        embeddings, timestamps = extract_speaker_segments(conversation_audio, encoder)
        
        # Cluster speakers
        labels = cluster_speakers(embeddings, n_speakers=2)
        
        # Match target speaker to clusters
        target_cluster, similarity = find_matching_speaker(target_embedding, embeddings, labels)
        
        # Reconstruct audio with only target speaker
        extracted_audio = reconstruct_audio(conversation_audio, labels, timestamps, target_cluster)
        
        # Apply volume boost if requested
        if extraction_file.boost_level != 'none':
            boost_multiplier = int(extraction_file.boost_level.replace('x', ''))
            extracted_audio = extracted_audio * boost_multiplier
            # Clip to prevent distortion
            extracted_audio = np.clip(extracted_audio, -1.0, 1.0)
        
        # Save extracted audio
        output_tensor = torch.from_numpy(extracted_audio).unsqueeze(0).float()
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_path = tmp_file.name
        
        torchaudio.save(tmp_path, output_tensor, 16000)
        
        # Save to model
        with open(tmp_path, 'rb') as f:
            filename = f"extracted_{extraction_file.original_filename}"
            extraction_file.extracted_file.save(filename, ContentFile(f.read()), save=False)
        
        # Clean up temp file
        os.remove(tmp_path)
        
        # Update status
        extraction_file.similarity_score = float(similarity)
        extraction_file.status = 'completed'
        extraction_file.processed_at = timezone.now()
        extraction_file.save()
        
    except Exception as e:
        extraction_file.status = 'error'
        extraction_file.error_message = str(e)
        extraction_file.save()
        print(f"Error processing speaker extraction {file_id}: {e}")
