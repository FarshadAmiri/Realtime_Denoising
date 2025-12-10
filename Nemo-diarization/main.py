"""
Main Pipeline Function
Unified interface for speaker diarization with optional transcription
"""

import os
from pathlib import Path
from typing import Optional, Dict, List
import json

from voice_enrollment import VoiceEnrollment
from diarization_processor import DiarizationProcessor
from transcription import TranscriptionProcessor


def process_meeting_audio(
    meeting_audio_path: str,
    voice_embeddings_database_path: str,
    expected_language: Optional[str] = None,
    output_transcriptions: bool = False,
    transcriptor_model_path: Optional[str] = None,
    num_speakers: Optional[int] = None,
    output_dir: Optional[str] = None
) -> Dict:
    """
    Complete pipeline for speaker diarization and optional transcription
    
    Args:
        meeting_audio_path: Path to the meeting/audio file to process
        voice_embeddings_database_path: Path to speaker embeddings database (JSON file)
        expected_language: Language code ('en', 'fa', 'ar', etc.) or None for auto-detect
        output_transcriptions: Whether to generate transcriptions
        transcriptor_model_path: Path to custom Whisper model (optional)
        num_speakers: Expected number of speakers (optional, will auto-detect if None)
        output_dir: Directory to save output files (optional)
    
    Returns:
        Dictionary containing:
            - segments: List of diarization segments with speaker labels
            - transcription: Transcribed text if output_transcriptions=True
            - num_speakers: Number of detected speakers
            - identified_speakers: List of identified speaker names
            - output_files: Paths to generated output files
    
    Example:
        result = process_meeting_audio(
            meeting_audio_path="meeting.wav",
            voice_embeddings_database_path="speakers.json",
            expected_language="en",
            output_transcriptions=True,
            transcriptor_model_path="whisper_medium.pt"
        )
    """
    
    # Validate inputs
    if not os.path.exists(meeting_audio_path):
        raise FileNotFoundError(f"Audio file not found: {meeting_audio_path}")
    
    if not os.path.exists(voice_embeddings_database_path):
        raise FileNotFoundError(f"Voice database not found: {voice_embeddings_database_path}")
    
    print("="*60)
    print("SPEAKER DIARIZATION PIPELINE")
    print("="*60)
    print(f"Audio file: {meeting_audio_path}")
    print(f"Voice database: {voice_embeddings_database_path}")
    print(f"Language: {expected_language or 'auto-detect'}")
    print(f"Transcription: {'enabled' if output_transcriptions else 'disabled'}")
    print("="*60)
    
    # Setup output directory
    if output_dir is None:
        output_dir = Path(meeting_audio_path).parent / "diarization_output"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_files = {}
    
    # ========== STEP 1: Load Voice Enrollment Database ==========
    print("\n[1/4] Loading speaker database...")
    voice_enrollment = VoiceEnrollment(voice_embeddings_database_path)
    enrolled_speakers = voice_enrollment.get_all_speakers()
    print(f"✓ Loaded {len(enrolled_speakers)} enrolled speakers: {enrolled_speakers}")
    
    # ========== STEP 2: Perform Diarization ==========
    print("\n[2/4] Performing speaker diarization...")
    diarization = DiarizationProcessor()
    diarization_segments = diarization.perform_diarization(
        meeting_audio_path,
        num_speakers=num_speakers
    )
    
    # Save raw diarization
    diarization_output = output_dir / "diarization_raw.json"
    diarization.save_diarization_results(
        diarization_segments,
        str(diarization_output),
        format="json"
    )
    output_files['diarization_raw'] = str(diarization_output)
    
    # ========== STEP 3: Identify Speakers ==========
    print("\n[3/4] Identifying speakers...")
    identified_segments = diarization.identify_speakers_in_segments(
        meeting_audio_path,
        diarization_segments,
        voice_enrollment
    )
    
    # Save identified diarization
    identified_output = output_dir / "diarization_identified.json"
    with open(identified_output, 'w') as f:
        json.dump(identified_segments, f, indent=2)
    output_files['diarization_identified'] = str(identified_output)
    
    # Count identified vs unidentified
    identified_count = sum(1 for s in identified_segments if s.get('identified', False))
    print(f"✓ Identified {identified_count}/{len(identified_segments)} segments")
    
    # Get unique identified speakers
    identified_speakers = list(set(
        s['speaker'] for s in identified_segments 
        if s.get('identified', False)
    ))
    
    # ========== STEP 4: Transcription (Optional) ==========
    combined_segments = identified_segments
    transcript_text = None
    
    if output_transcriptions:
        print("\n[4/4] Generating transcriptions...")
        
        # Check if transcriptor_model_path is valid
        if transcriptor_model_path and not os.path.exists(transcriptor_model_path):
            print(f"⚠ Warning: Transcriptor model not found at {transcriptor_model_path}")
            print("  Using default Whisper model instead")
            transcriptor_model_path = None
        
        transcriptor = TranscriptionProcessor(
            model_path=transcriptor_model_path,
            model_name="base"  # Fallback model
        )
        
        # Transcribe
        transcription_result = transcriptor.transcribe_audio(
            meeting_audio_path,
            language=expected_language
        )
        
        # Align with diarization
        combined_segments = transcriptor.align_transcription_with_diarization(
            transcription_result['segments'],
            identified_segments
        )
        
        # Merge adjacent segments
        combined_segments = transcriptor.merge_adjacent_segments(combined_segments)
        
        # Save in multiple formats
        formats = {
            'json': 'transcript.json',
            'text': 'transcript.txt',
            'srt': 'transcript.srt',
            'vtt': 'transcript.vtt'
        }
        
        for fmt, filename in formats.items():
            output_path = output_dir / filename
            transcriptor.save_transcript(combined_segments, str(output_path), format=fmt)
            output_files[f'transcript_{fmt}'] = str(output_path)
        
        # Generate plain text transcript
        transcript_text = transcriptor.format_transcript(combined_segments, format='text')
        
        print("✓ Transcription complete")
    else:
        print("\n[4/4] Skipping transcription (disabled)")
    
    # ========== Generate Summary ==========
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    
    num_detected_speakers = len(set(s['speaker'] for s in identified_segments))
    print(f"Detected speakers: {num_detected_speakers}")
    print(f"Identified speakers: {identified_speakers}")
    print(f"Total segments: {len(identified_segments)}")
    print(f"Output directory: {output_dir}")
    print("="*60)
    
    # Prepare return dictionary
    result = {
        'segments': combined_segments,
        'num_speakers': num_detected_speakers,
        'identified_speakers': identified_speakers,
        'enrolled_speakers': enrolled_speakers,
        'output_files': output_files,
        'output_dir': str(output_dir)
    }
    
    if output_transcriptions and transcript_text:
        result['transcription'] = transcript_text
    
    return result


def quick_diarize(
    audio_path: str,
    database_path: str,
    output_dir: Optional[str] = None
) -> Dict:
    """
    Quick diarization without transcription
    
    Args:
        audio_path: Path to audio file
        database_path: Path to speaker database
        output_dir: Output directory
    
    Returns:
        Diarization results
    """
    return process_meeting_audio(
        meeting_audio_path=audio_path,
        voice_embeddings_database_path=database_path,
        output_transcriptions=False,
        output_dir=output_dir
    )


def diarize_and_transcribe(
    audio_path: str,
    database_path: str,
    language: str = "en",
    whisper_model: Optional[str] = None,
    output_dir: Optional[str] = None
) -> Dict:
    """
    Diarization with transcription
    
    Args:
        audio_path: Path to audio file
        database_path: Path to speaker database
        language: Language code
        whisper_model: Path to Whisper model
        output_dir: Output directory
    
    Returns:
        Complete results with transcription
    """
    return process_meeting_audio(
        meeting_audio_path=audio_path,
        voice_embeddings_database_path=database_path,
        expected_language=language,
        output_transcriptions=True,
        transcriptor_model_path=whisper_model,
        output_dir=output_dir
    )
