"""
Simple Example: Quick Start with Diarization
"""

from main import process_meeting_audio, quick_diarize, diarize_and_transcribe
from voice_enrollment import create_voice_database

# ============================================
# Example 1: Create Speaker Database
# ============================================

print("Example 1: Creating speaker database...")

speaker_samples = {
    "John": ["samples/john_voice.wav"],
    "Jane": ["samples/jane_voice1.wav", "samples/jane_voice2.wav"],
    "Ali": ["samples/ali_voice.wav"]
}

enrollment = create_voice_database(
    database_path="speakers.json",
    speaker_samples=speaker_samples
)

print(f"✓ Database created with {len(enrollment.get_all_speakers())} speakers\n")


# ============================================
# Example 2: Quick Diarization (No Transcription)
# ============================================

print("Example 2: Quick diarization...")

result = quick_diarize(
    audio_path="meeting_audio.wav",
    database_path="speakers.json",
    output_dir="output"
)

print(f"✓ Detected {result['num_speakers']} speakers")
print(f"✓ Identified: {result['identified_speakers']}\n")


# ============================================
# Example 3: Diarization with Transcription
# ============================================

print("Example 3: Diarization with transcription...")

result = diarize_and_transcribe(
    audio_path="meeting_audio.wav",
    database_path="speakers.json",
    language="en",
    output_dir="output_with_transcript"
)

# Print first few segments
print("\nFirst 5 segments:")
for seg in result['segments'][:5]:
    print(f"[{seg['start']:.2f}-{seg['end']:.2f}] {seg['speaker']}: {seg.get('text', 'N/A')}")

print(f"\n✓ Complete! Files saved to: {result['output_dir']}")


# ============================================
# Example 4: Full Control
# ============================================

print("\nExample 4: Full control over parameters...")

result = process_meeting_audio(
    meeting_audio_path="meeting_audio.wav",
    voice_embeddings_database_path="speakers.json",
    expected_language="fa",  # Persian
    output_transcriptions=True,
    transcriptor_model_path="whisper_persian_finetuned.pt",  # Custom model
    num_speakers=3,  # Expect 3 speakers
    output_dir="output_persian"
)

print(f"✓ Processed {len(result['segments'])} segments")
print(f"✓ Identified speakers: {result['identified_speakers']}")

if 'transcription' in result:
    print("\nFull transcript:")
    print(result['transcription'])
