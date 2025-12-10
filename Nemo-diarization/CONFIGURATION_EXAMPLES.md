# Configuration Examples

## Scenario 1: English Business Meeting

```python
result = process_meeting_audio(
    meeting_audio_path="business_meeting.wav",
    voice_embeddings_database_path="team_members.json",
    expected_language="en",
    output_transcriptions=True,
    num_speakers=5,  # Expected 5 participants
    output_dir="meeting_2024_12_10"
)
```

## Scenario 2: Persian Podcast

```python
result = process_meeting_audio(
    meeting_audio_path="podcast_farsi.mp3",
    voice_embeddings_database_path="hosts_farsi.json",
    expected_language="fa",
    output_transcriptions=True,
    transcriptor_model_path="models/whisper_persian_medium.pt",
    num_speakers=2,  # Host + Guest
    output_dir="podcast_episode_15"
)
```

## Scenario 3: Multilingual Conference

```python
# Auto-detect language
result = process_meeting_audio(
    meeting_audio_path="international_conference.wav",
    voice_embeddings_database_path="speakers_international.json",
    expected_language=None,  # Auto-detect
    output_transcriptions=True,
    output_dir="conference_2024"
)
```

## Scenario 4: Quick Analysis (No Transcription)

```python
# Fast diarization without transcription
result = quick_diarize(
    audio_path="meeting_quick.wav",
    database_path="speakers.json"
)

# Just check who spoke
for seg in result['segments']:
    print(f"{seg['speaker']}: {seg['end']-seg['start']:.1f}s")
```

## Scenario 5: Legal Deposition

```python
# High accuracy, custom model
result = process_meeting_audio(
    meeting_audio_path="deposition_2024.wav",
    voice_embeddings_database_path="legal_speakers.json",
    expected_language="en",
    output_transcriptions=True,
    transcriptor_model_path="models/whisper_large.pt",  # Best accuracy
    num_speakers=3,  # Attorney, witness, court reporter
    output_dir="case_12345/deposition"
)
```

## Scenario 6: Customer Service Call

```python
# Two speakers (agent + customer)
result = process_meeting_audio(
    meeting_audio_path="support_call_1234.wav",
    voice_embeddings_database_path="support_agents.json",
    expected_language="en",
    output_transcriptions=True,
    num_speakers=2,
    output_dir="calls/2024_12_10/call_1234"
)
```

## Scenario 7: Educational Lecture

```python
# Single known speaker (professor) + Q&A
result = process_meeting_audio(
    meeting_audio_path="lecture_cs101.wav",
    voice_embeddings_database_path="professors.json",
    expected_language="en",
    output_transcriptions=True,
    output_dir="lectures/cs101/week_12"
)
```

## Scenario 8: Medical Consultation

```python
# Doctor + Patient
result = process_meeting_audio(
    meeting_audio_path="consultation_anonymous.wav",
    voice_embeddings_database_path="doctors.json",
    expected_language="en",
    output_transcriptions=True,
    num_speakers=2,
    output_dir="consultations/2024_12"
)
```

## Scenario 9: Batch Processing Daily Meetings

```python
from utils import batch_process_meetings

# Process all meetings from today
batch_process_meetings(
    audio_dir="meetings/2024_12_10/",
    database_path="company_speakers.json",
    output_base_dir="processed/2024_12_10/",
    expected_language="en",
    output_transcriptions=True
)
```

## Scenario 10: Research Interview

```python
# Researcher + Participant
result = process_meeting_audio(
    meeting_audio_path="interview_participant_42.wav",
    voice_embeddings_database_path="research_team.json",
    expected_language="en",
    output_transcriptions=True,
    transcriptor_model_path="models/whisper_medium.pt",
    num_speakers=2,
    output_dir="research_study/interviews/p42"
)

# Extract only participant's audio
from utils import extract_speaker_audio
extract_speaker_audio(
    audio_path="interview_participant_42.wav",
    segments=result['segments'],
    speaker_name="Participant_42",
    output_path="p42_responses_only.wav"
)
```

## Performance Tuning

### Fast Processing (CPU)

```python
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Disable GPU

result = quick_diarize(
    audio_path="meeting.wav",
    database_path="speakers.json"
)
```

### Maximum Accuracy (GPU)

```python
result = process_meeting_audio(
    meeting_audio_path="important_meeting.wav",
    voice_embeddings_database_path="speakers.json",
    expected_language="en",
    output_transcriptions=True,
    transcriptor_model_path="models/whisper_large.pt",  # Best model
    output_dir="critical_meeting"
)
```

### Balanced (Recommended)

```python
result = process_meeting_audio(
    meeting_audio_path="meeting.wav",
    voice_embeddings_database_path="speakers.json",
    expected_language="en",
    output_transcriptions=True,
    # Uses base Whisper model by default - good balance
    output_dir="meeting_output"
)
```

## Environment-Specific Configurations

### Development/Testing

```python
# Quick iterations
result = quick_diarize("test.wav", "test_speakers.json")
```

### Staging

```python
# Full pipeline with monitoring
result = diarize_and_transcribe(
    audio_path="staging_meeting.wav",
    database_path="staging_speakers.json",
    language="en",
    output_dir="staging_output"
)
```

### Production

```python
# With error handling and logging
import logging
logging.basicConfig(level=logging.INFO)

try:
    result = process_meeting_audio(
        meeting_audio_path=audio_path,
        voice_embeddings_database_path=prod_database,
        expected_language=detected_language,
        output_transcriptions=True,
        output_dir=unique_output_dir
    )
    
    # Save to database
    save_results_to_db(result)
    
    # Notify users
    notify_completion(result)
    
except Exception as e:
    logging.error(f"Diarization failed: {e}")
    notify_error(e)
```

## Language-Specific Configurations

### English (US/UK)

```python
result = process_meeting_audio(
    ...,
    expected_language="en"
)
```

### Persian/Farsi

```python
result = process_meeting_audio(
    ...,
    expected_language="fa",
    transcriptor_model_path="whisper_persian_finetuned.pt"
)
```

### Arabic

```python
result = process_meeting_audio(
    ...,
    expected_language="ar"
)
```

### Chinese

```python
result = process_meeting_audio(
    ...,
    expected_language="zh"
)
```

### Spanish

```python
result = process_meeting_audio(
    ...,
    expected_language="es"
)
```

### Mixed/Auto-detect

```python
result = process_meeting_audio(
    ...,
    expected_language=None  # Will auto-detect
)
```
