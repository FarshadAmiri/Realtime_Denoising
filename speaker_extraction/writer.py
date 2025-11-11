#!/usr/bin/env python3
code = r'''import os
import torch
import torchaudio
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
from spectralcluster import SpectralClusterer
from pathlib import Path

TARGET_SAMPLE = r"C:\Users\User_1\Desktop\speeches\1\3000_sample.wav"
CONVERSATION = r"C:\Users\User_1\Desktop\speeches\1\concat_1.wav"
OUTPUT_DIR = r"C:\Users\User_1\Desktop\speeches\1"

def load_and_preprocess(audio_path):
    waveform, sr = torchaudio.load(audio_path)
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)
    audio_np = waveform.squeeze().numpy()
    preprocessed = preprocess_wav(audio_np, source_sr=sr)
    return preprocessed, sr

def extract_speaker_segments(audio, encoder, window_sec=1.5, overlap=0.5):
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
    clusterer = SpectralClusterer(
        min_clusters=n_speakers,
        max_clusters=n_speakers,
        p_percentile=0.95,
        gaussian_blur_sigma=1
    )
    labels = clusterer.predict(embeddings)
    return labels

def find_matching_speaker(target_embedding, conversation_embeddings, labels):
    unique_labels = np.unique(labels)
    cluster_similarities = []
    for label in unique_labels:
        cluster_mask = labels == label
        cluster_embeddings = conversation_embeddings[cluster_mask]
        similarities = [np.dot(target_embedding, emb) / (np.linalg.norm(target_embedding) * np.linalg.norm(emb)) 
                       for emb in cluster_embeddings]
        avg_similarity = np.mean(similarities)
        cluster_similarities.append((label, avg_similarity))
        print(f"Cluster {label}: {len(cluster_embeddings)} segments, avg similarity = {avg_similarity:.4f}")
    best_cluster = max(cluster_similarities, key=lambda x: x[1])
    return best_cluster[0], best_cluster[1]

def reconstruct_audio(audio, labels, timestamps, target_label):
    sr = 16000
    output_audio = np.zeros_like(audio)
    for i, (start_time, end_time) in enumerate(timestamps):
        if labels[i] == target_label:
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            output_audio[start_sample:end_sample] = audio[start_sample:end_sample]
    return output_audio

def main():
    print("Initializing voice encoder...")
    encoder = VoiceEncoder()
    print("\nLoading target speaker sample...")
    target_audio, _ = load_and_preprocess(TARGET_SAMPLE)
    target_embedding = encoder.embed_utterance(target_audio)
    print(f"Target sample: {len(target_audio)/16000:.2f} seconds")
    print("\nLoading conversation...")
    conversation_audio, conv_sr = load_and_preprocess(CONVERSATION)
    print(f"Conversation: {len(conversation_audio)/16000:.2f} seconds")
    print("\nExtracting speaker embeddings from conversation...")
    embeddings, timestamps = extract_speaker_segments(conversation_audio, encoder)
    print(f"Extracted {len(embeddings)} segments")
    print("\nClustering speakers...")
    labels = cluster_speakers(embeddings, n_speakers=2)
    print("\nMatching target speaker to clusters...")
    target_cluster, similarity = find_matching_speaker(target_embedding, embeddings, labels)
    print(f"\nBest match: Cluster {target_cluster} (similarity: {similarity:.4f})")
    print("\nReconstructing audio with only target speaker...")
    extracted_audio = reconstruct_audio(conversation_audio, labels, timestamps, target_cluster)
    output_path = os.path.join(OUTPUT_DIR, "target_voice_extracted.wav")
    output_tensor = torch.from_numpy(extracted_audio).unsqueeze(0).float()
    torchaudio.save(output_path, output_tensor, 16000)
    print(f"\nOutput saved to: {output_path}")
    for cluster_id in np.unique(labels):
        cluster_audio = reconstruct_audio(conversation_audio, labels, timestamps, cluster_id)
        cluster_path = os.path.join(OUTPUT_DIR, f"speaker_cluster_{cluster_id}.wav")
        cluster_tensor = torch.from_numpy(cluster_audio).unsqueeze(0).float()
        torchaudio.save(cluster_path, cluster_tensor, 16000)
        print(f"Saved cluster {cluster_id} to: {cluster_path}")
    print("\nDone!")

if __name__ == "__main__":
    main()
'''

with open(r'd:\Git_repos\Realtime_Denoising\speaker_extraction\extract_speaker.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("File created!")
