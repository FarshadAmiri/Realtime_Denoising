"""
Utility functions for Nemo-Diarization
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import torchaudio
import numpy as np


def convert_audio_format(input_path: str, output_path: str, target_sr: int = 16000):
    """
    Convert audio to desired format and sample rate
    
    Args:
        input_path: Input audio file
        output_path: Output audio file
        target_sr: Target sample rate (default: 16000)
    """
    waveform, sr = torchaudio.load(input_path)
    
    # Resample if needed
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(sr, target_sr)
        waveform = resampler(waveform)
    
    # Convert to mono if stereo
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)
    
    torchaudio.save(output_path, waveform, target_sr)
    print(f"✓ Converted: {input_path} → {output_path}")


def validate_audio_file(audio_path: str) -> bool:
    """
    Validate audio file format and accessibility
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        True if valid, False otherwise
    """
    if not os.path.exists(audio_path):
        print(f"✗ File not found: {audio_path}")
        return False
    
    try:
        waveform, sr = torchaudio.load(audio_path)
        duration = waveform.shape[1] / sr
        
        print(f"✓ Valid audio file")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Sample rate: {sr}Hz")
        print(f"  Channels: {waveform.shape[0]}")
        return True
    except Exception as e:
        print(f"✗ Invalid audio file: {e}")
        return False


def merge_speaker_databases(db_paths: List[str], output_path: str):
    """
    Merge multiple speaker databases into one
    
    Args:
        db_paths: List of database JSON files
        output_path: Output merged database path
    """
    merged = {}
    
    for db_path in db_paths:
        with open(db_path, 'r') as f:
            data = json.load(f)
            merged.update(data)
    
    with open(output_path, 'w') as f:
        json.dump(merged, f, indent=2)
    
    print(f"✓ Merged {len(db_paths)} databases → {output_path}")
    print(f"  Total speakers: {len(merged)}")


def export_segments_to_csv(segments: List[Dict], output_path: str):
    """
    Export segments to CSV format
    
    Args:
        segments: List of segment dictionaries
        output_path: Output CSV file path
    """
    import csv
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['start', 'end', 'duration', 'speaker', 'identified', 'text']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for seg in segments:
            row = {
                'start': f"{seg['start']:.2f}",
                'end': f"{seg['end']:.2f}",
                'duration': f"{seg['end'] - seg['start']:.2f}",
                'speaker': seg['speaker'],
                'identified': seg.get('identified', False),
                'text': seg.get('text', '')
            }
            writer.writerow(row)
    
    print(f"✓ Exported {len(segments)} segments to {output_path}")


def calculate_speaker_statistics(segments: List[Dict]) -> Dict:
    """
    Calculate speaking time statistics
    
    Args:
        segments: List of segment dictionaries
        
    Returns:
        Dictionary with speaker statistics
    """
    from collections import defaultdict
    
    stats = defaultdict(lambda: {'duration': 0.0, 'segments': 0})
    total_duration = 0.0
    
    for seg in segments:
        speaker = seg['speaker']
        duration = seg['end'] - seg['start']
        
        stats[speaker]['duration'] += duration
        stats[speaker]['segments'] += 1
        total_duration += duration
    
    # Calculate percentages
    for speaker in stats:
        stats[speaker]['percentage'] = (stats[speaker]['duration'] / total_duration) * 100
    
    return dict(stats)


def print_statistics(segments: List[Dict]):
    """
    Print detailed statistics about segments
    
    Args:
        segments: List of segment dictionaries
    """
    stats = calculate_speaker_statistics(segments)
    
    print("\n" + "="*60)
    print("SPEAKER STATISTICS")
    print("="*60)
    
    for speaker, data in sorted(stats.items(), key=lambda x: x[1]['duration'], reverse=True):
        print(f"\n{speaker}:")
        print(f"  Speaking time: {data['duration']:.1f}s")
        print(f"  Percentage: {data['percentage']:.1f}%")
        print(f"  Segments: {data['segments']}")
        print(f"  Avg segment: {data['duration']/data['segments']:.1f}s")
    
    total_duration = sum(s['duration'] for s in stats.values())
    print(f"\n{'='*60}")
    print(f"Total speaking time: {total_duration:.1f}s")
    print(f"Total segments: {len(segments)}")
    print("="*60)


def extract_speaker_audio(
    audio_path: str,
    segments: List[Dict],
    speaker_name: str,
    output_path: str
):
    """
    Extract all audio segments for a specific speaker
    
    Args:
        audio_path: Input audio file
        segments: List of segments
        speaker_name: Speaker to extract
        output_path: Output audio file
    """
    import torch
    
    waveform, sr = torchaudio.load(audio_path)
    
    # Filter segments for speaker
    speaker_segments = [s for s in segments if s['speaker'] == speaker_name]
    
    if not speaker_segments:
        print(f"✗ No segments found for speaker: {speaker_name}")
        return
    
    # Extract and concatenate
    audio_chunks = []
    for seg in speaker_segments:
        start_sample = int(seg['start'] * sr)
        end_sample = int(seg['end'] * sr)
        chunk = waveform[:, start_sample:end_sample]
        audio_chunks.append(chunk)
    
    # Concatenate
    combined = torch.cat(audio_chunks, dim=1)
    
    # Save
    torchaudio.save(output_path, combined, sr)
    
    total_duration = sum(s['end'] - s['start'] for s in speaker_segments)
    print(f"✓ Extracted {speaker_name} audio:")
    print(f"  Duration: {total_duration:.2f}s")
    print(f"  Segments: {len(speaker_segments)}")
    print(f"  Saved to: {output_path}")


def create_speaker_timeline(segments: List[Dict], output_path: str):
    """
    Create a visual timeline of speakers
    
    Args:
        segments: List of segments
        output_path: Output image path
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        
        # Get unique speakers
        speakers = sorted(set(s['speaker'] for s in segments))
        speaker_to_idx = {s: i for i, s in enumerate(speakers)}
        
        # Create colors
        colors = plt.cm.Set3(range(len(speakers)))
        
        # Create plot
        fig, ax = plt.subplots(figsize=(15, len(speakers)))
        
        for seg in segments:
            speaker = seg['speaker']
            idx = speaker_to_idx[speaker]
            duration = seg['end'] - seg['start']
            
            rect = Rectangle(
                (seg['start'], idx - 0.4),
                duration,
                0.8,
                facecolor=colors[idx],
                edgecolor='black',
                linewidth=0.5
            )
            ax.add_patch(rect)
        
        # Format
        ax.set_xlim(0, segments[-1]['end'])
        ax.set_ylim(-0.5, len(speakers) - 0.5)
        ax.set_yticks(range(len(speakers)))
        ax.set_yticklabels(speakers)
        ax.set_xlabel('Time (seconds)')
        ax.set_title('Speaker Timeline')
        ax.grid(True, axis='x', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        
        print(f"✓ Timeline saved to: {output_path}")
    except ImportError:
        print("✗ matplotlib required for timeline visualization")
        print("  Install: pip install matplotlib")


def batch_process_meetings(
    audio_dir: str,
    database_path: str,
    output_base_dir: str,
    **kwargs
):
    """
    Process multiple meeting audio files in batch
    
    Args:
        audio_dir: Directory containing audio files
        database_path: Speaker database path
        output_base_dir: Base output directory
        **kwargs: Additional arguments for process_meeting_audio
    """
    from main import process_meeting_audio
    
    audio_dir = Path(audio_dir)
    output_base_dir = Path(output_base_dir)
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    # Find audio files
    audio_files = []
    for ext in ['*.wav', '*.mp3', '*.m4a', '*.flac']:
        audio_files.extend(audio_dir.glob(ext))
    
    print(f"Found {len(audio_files)} audio files")
    print("="*60)
    
    results = []
    for i, audio_path in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}] Processing: {audio_path.name}")
        
        output_dir = output_base_dir / audio_path.stem
        
        try:
            result = process_meeting_audio(
                meeting_audio_path=str(audio_path),
                voice_embeddings_database_path=database_path,
                output_dir=str(output_dir),
                **kwargs
            )
            results.append({
                'file': audio_path.name,
                'status': 'success',
                'speakers': result['num_speakers'],
                'identified': result['identified_speakers']
            })
        except Exception as e:
            print(f"✗ Error processing {audio_path.name}: {e}")
            results.append({
                'file': audio_path.name,
                'status': 'error',
                'error': str(e)
            })
    
    # Save summary
    summary_path = output_base_dir / 'batch_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*60)
    print("BATCH PROCESSING COMPLETE")
    print("="*60)
    print(f"Processed: {len(audio_files)} files")
    print(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"Failed: {sum(1 for r in results if r['status'] == 'error')}")
    print(f"Summary: {summary_path}")
    print("="*60)
