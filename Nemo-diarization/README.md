# Nemo-Diarization System

Speaker Diarization and Identification with Optional Transcription

## Features

- **Speaker Diarization**: Detect "who spoke when" in audio recordings
- **Speaker Identification**: Match speakers to known voice profiles
- **Transcription**: Optional speech-to-text with speaker labels
- **Multi-language Support**: Works with any language (language-agnostic diarization)
- **Multiple Output Formats**: JSON, TXT, SRT, VTT, RTTM

## Architecture

- **SpeechBrain**: Speaker recognition and embedding extraction
- **Resemblyzer**: Fast speaker verification and identification
- **Whisper**: Speech-to-text transcription
- **Sklearn**: Speaker clustering algorithms

## Installation

Already included in your ClearCast environment. No additional packages needed!

Required packages (already installed):
- speechbrain
- resemblyzer
- openai-whisper
- torch
- torchaudio
- scikit-learn

## Quick Start

### 1. Create Speaker Database

```python
from voice_enrollment import create_voice_database

# Prepare speaker samples
speaker_samples = {
    "John": ["john_sample1.wav", "john_sample2.wav"],
    "Jane": ["jane_sample1.wav"],
    "Ali": ["ali_sample.wav"]
}

# Create database
enrollment = create_voice_database(
    database_path="speakers.json",
    speaker_samples=speaker_samples
)
```

### 2. Process Meeting Audio

```python
from main import process_meeting_audio

# Diarization only
result = process_meeting_audio(
    meeting_audio_path="meeting.wav",
    voice_embeddings_database_path="speakers.json",
    output_transcriptions=False
)

# Diarization + Transcription
result = process_meeting_audio(
    meeting_audio_path="meeting.wav",
    voice_embeddings_database_path="speakers.json",
    expected_language="en",  # or "fa" for Persian
    output_transcriptions=True,
    transcriptor_model_path="path/to/whisper_model.pt"  # optional
)
```

### 3. Access Results

```python
# Diarization segments
for segment in result['segments']:
    print(f"[{segment['start']:.2f} - {segment['end']:.2f}] {segment['speaker']}")
    if 'text' in segment:
        print(f"  {segment['text']}")

# Identified speakers
print(f"Speakers: {result['identified_speakers']}")

# Full transcript (if transcription enabled)
if 'transcription' in result:
    print(result['transcription'])

# Output files
print(f"Files saved to: {result['output_dir']}")
```

## Output Files

The system generates:

- `diarization_raw.json` - Raw diarization without speaker identification
- `diarization_identified.json` - Diarization with identified speakers
- `transcript.json` - Complete transcript with timestamps (if enabled)
- `transcript.txt` - Plain text transcript (if enabled)
- `transcript.srt` - SRT subtitles (if enabled)
- `transcript.vtt` - WebVTT subtitles (if enabled)

## Function Parameters

### `process_meeting_audio()`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `meeting_audio_path` | str | Yes | Path to audio file |
| `voice_embeddings_database_path` | str | Yes | Path to speaker database JSON |
| `expected_language` | str | No | Language code ('en', 'fa', 'ar', etc.) |
| `output_transcriptions` | bool | No | Enable transcription (default: False) |
| `transcriptor_model_path` | str | No | Path to custom Whisper model |
| `num_speakers` | int | No | Expected number of speakers |
| `output_dir` | str | No | Output directory path |

## Supported Languages

Diarization works for **all languages** (language-agnostic).

Transcription supports:
- English (en)
- Persian/Farsi (fa)
- Arabic (ar)
- And 90+ other languages supported by Whisper

## Performance Tips

1. **GPU Acceleration**: Automatically uses CUDA if available
2. **Audio Quality**: Higher quality audio = better diarization
3. **Multiple Samples**: Enroll speakers with 2-3 samples for better accuracy
4. **Segment Length**: Default 1.5s windows work well for most cases

## API Reference

### VoiceEnrollment

```python
enrollment = VoiceEnrollment("speakers.json")

# Enroll single speaker
enrollment.enroll_speaker("John", "john.wav")

# Enroll with multiple samples
enrollment.enroll_multiple_samples("Jane", ["jane1.wav", "jane2.wav"])

# Save database
enrollment.save_database()

# Identify unknown speaker
speaker_name = enrollment.identify_speaker(embedding, threshold=0.75)
```

### DiarizationProcessor

```python
diarizer = DiarizationProcessor(device="cuda")

# Perform diarization
segments = diarizer.perform_diarization(
    "meeting.wav",
    num_speakers=3,
    window_size=1.5,
    hop_size=0.75
)

# Identify speakers
identified = diarizer.identify_speakers_in_segments(
    "meeting.wav",
    segments,
    voice_enrollment
)
```

### TranscriptionProcessor

```python
transcriptor = TranscriptionProcessor(model_path="whisper_model.pt")

# Transcribe
result = transcriptor.transcribe_audio("meeting.wav", language="en")

# Align with diarization
combined = transcriptor.align_transcription_with_diarization(
    result['segments'],
    diarization_segments
)

# Save transcript
transcriptor.save_transcript(combined, "transcript.txt", format="text")
```

## Troubleshooting

**Issue**: Out of memory error
- Solution: Use smaller Whisper model or process on CPU

**Issue**: Poor speaker identification
- Solution: Enroll speakers with longer/multiple samples

**Issue**: Too many/few speakers detected
- Solution: Specify `num_speakers` parameter explicitly

**Issue**: Incorrect language detection
- Solution: Specify `expected_language` parameter

## Integration with ClearCast

This module can be integrated into your Django/FastAPI endpoints:

```python
from Nemo_diarization.main import process_meeting_audio

def process_uploaded_meeting(audio_file_path):
    result = process_meeting_audio(
        meeting_audio_path=audio_file_path,
        voice_embeddings_database_path="media/speakers/database.json",
        expected_language="en",
        output_transcriptions=True
    )
    return result
```

## Credits

- SpeechBrain: ECAPA-TDNN speaker recognition
- Resemblyzer: Fast speaker verification
- OpenAI Whisper: Speech recognition
- Built for ClearCast audio processing platform
