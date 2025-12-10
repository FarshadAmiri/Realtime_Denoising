# Quick Start Guide - Nemo-Diarization

## 🚀 5-Minute Quick Start

### Step 1: Prepare Speaker Voice Samples

Collect 1-3 short audio clips (5-30 seconds each) for each person you want to identify.

```
samples/
├── john_voice.wav
├── jane_voice1.wav
├── jane_voice2.wav
└── ali_voice.wav
```

### Step 2: Open Jupyter Notebook

```bash
cd Nemo-diarization
jupyter notebook test_diarization.ipynb
```

### Step 3: Update Configuration

In cell 2 of the notebook, update these paths:

```python
MEETING_AUDIO = "path/to/your/meeting.wav"

SPEAKER_SAMPLES = {
    "John": ["samples/john_voice.wav"],
    "Jane": ["samples/jane_voice1.wav", "samples/jane_voice2.wav"],
    "Ali": ["samples/ali_voice.wav"]
}

LANGUAGE = "en"  # or "fa" for Persian
```

### Step 4: Run All Cells

Execute all cells in the notebook. The system will:
1. ✅ Create speaker database
2. ✅ Perform diarization
3. ✅ Identify speakers
4. ✅ Generate transcripts (if enabled)

### Step 5: Check Results

Results are saved in `diarization_output/`:
- `transcript.txt` - Plain text transcript with speakers
- `transcript.srt` - Subtitles for video
- `diarization_identified.json` - Complete data

## 📋 Function Signature

```python
def process_meeting_audio(
    meeting_audio_path: str,              # Path to audio file
    voice_embeddings_database_path: str,  # Path to speakers.json
    expected_language: str = None,        # 'en', 'fa', 'ar', or None
    output_transcriptions: bool = False,  # Enable transcription?
    transcriptor_model_path: str = None,  # Custom Whisper model
    num_speakers: int = None,             # Expected # of speakers
    output_dir: str = None                # Output directory
) -> Dict
```

## 💡 Common Use Cases

### Use Case 1: Meeting Notes with Speaker Labels

```python
from main import process_meeting_audio

result = process_meeting_audio(
    meeting_audio_path="team_meeting.wav",
    voice_embeddings_database_path="team_speakers.json",
    expected_language="en",
    output_transcriptions=True
)

# Read transcript
with open(f"{result['output_dir']}/transcript.txt", 'r') as f:
    print(f.read())
```

### Use Case 2: Podcast Diarization

```python
from main import quick_diarize

result = quick_diarize(
    audio_path="podcast_episode.mp3",
    database_path="hosts_database.json"
)

# See who spoke when
for seg in result['segments']:
    print(f"[{seg['start']:.0f}:{seg['end']:.0f}] {seg['speaker']}")
```

### Use Case 3: Interview Transcription

```python
from main import diarize_and_transcribe

result = diarize_and_transcribe(
    audio_path="interview.wav",
    database_path="speakers.json",
    language="en",
    output_dir="interview_output"
)

# Export to SRT for video subtitles
srt_path = f"{result['output_dir']}/transcript.srt"
print(f"Subtitles: {srt_path}")
```

### Use Case 4: Persian Language Support

```python
result = process_meeting_audio(
    meeting_audio_path="jalase_farsi.wav",
    voice_embeddings_database_path="speakers_farsi.json",
    expected_language="fa",
    output_transcriptions=True,
    transcriptor_model_path="whisper_persian_finetuned.pt"
)
```

## 🔧 Troubleshooting

### Problem: "CUDA out of memory"

**Solution 1**: Use smaller Whisper model
```python
transcriptor_model_path=None  # Uses 'base' model
```

**Solution 2**: Process on CPU
```python
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
```

### Problem: Speaker identification accuracy is low

**Solution 1**: Use multiple voice samples per speaker
```python
speaker_samples = {
    "John": ["john1.wav", "john2.wav", "john3.wav"]  # Better!
}
```

**Solution 2**: Use longer voice samples (10-30 seconds)

**Solution 3**: Lower identification threshold
```python
# In voice_enrollment.py, modify:
identified = enrollment.identify_speaker(embedding, threshold=0.65)  # Lower = more lenient
```

### Problem: Wrong number of speakers detected

**Solution**: Specify expected number
```python
result = process_meeting_audio(
    ...,
    num_speakers=3  # Explicitly set to 3 speakers
)
```

### Problem: Transcription in wrong language

**Solution**: Specify language explicitly
```python
result = process_meeting_audio(
    ...,
    expected_language="fa"  # Force Persian
)
```

## 📊 Understanding Output

### Segment Structure

```python
{
    "start": 0.0,           # Start time in seconds
    "end": 5.2,             # End time in seconds
    "speaker": "John",      # Identified speaker name
    "identified": True,     # Was speaker identified?
    "text": "Hello..."      # Transcribed text (if enabled)
}
```

### Result Dictionary

```python
{
    "segments": [...],                    # List of segments
    "num_speakers": 3,                    # Number of speakers
    "identified_speakers": ["John", "Jane"],  # Identified speakers
    "enrolled_speakers": ["John", "Jane", "Ali"],  # All in database
    "transcription": "Full text...",      # Full transcript (if enabled)
    "output_files": {...},                # Paths to output files
    "output_dir": "diarization_output"    # Output directory
}
```

## 🎯 Best Practices

### 1. Voice Sample Quality

✅ **Good**:
- Clear speech without background noise
- 10-30 seconds duration
- Natural speaking voice
- Multiple samples per speaker

❌ **Avoid**:
- Music or heavy background noise
- Too short (<5 seconds)
- Shouting or whispering
- Phone/radio quality

### 2. Meeting Audio Quality

✅ **Good**:
- Clear recording
- All speakers audible
- Minimal overlap
- WAV format (lossless)

❌ **Avoid**:
- Heavy noise
- Multiple people talking simultaneously
- Very low volume
- Heavy compression

### 3. Performance Optimization

```python
# For faster processing (no transcription)
result = quick_diarize(audio_path, database_path)

# For complete results (with transcription)
result = diarize_and_transcribe(audio_path, database_path, language="en")
```

## 🔗 Integration Examples

### Django View

```python
from django.http import JsonResponse
from Nemo_diarization.main import process_meeting_audio

def diarize_uploaded_audio(request):
    audio_file = request.FILES['audio']
    audio_path = save_upload(audio_file)
    
    result = process_meeting_audio(
        meeting_audio_path=audio_path,
        voice_embeddings_database_path="media/speakers.json",
        expected_language="en",
        output_transcriptions=True
    )
    
    return JsonResponse({
        'speakers': result['identified_speakers'],
        'transcript': result.get('transcription', ''),
        'segments': result['segments']
    })
```

### FastAPI Endpoint

```python
from fastapi import FastAPI, UploadFile
from Nemo_diarization.main import process_meeting_audio

app = FastAPI()

@app.post("/diarize")
async def diarize(audio: UploadFile, transcribe: bool = False):
    # Save uploaded file
    audio_path = f"temp/{audio.filename}"
    with open(audio_path, 'wb') as f:
        f.write(await audio.read())
    
    # Process
    result = process_meeting_audio(
        meeting_audio_path=audio_path,
        voice_embeddings_database_path="speakers.json",
        output_transcriptions=transcribe
    )
    
    return result
```

### Celery Task (Async)

```python
from celery import shared_task
from Nemo_diarization.main import process_meeting_audio

@shared_task
def process_meeting_async(audio_id, database_path):
    audio = Audio.objects.get(id=audio_id)
    
    result = process_meeting_audio(
        meeting_audio_path=audio.file.path,
        voice_embeddings_database_path=database_path,
        output_transcriptions=True
    )
    
    # Save results to database
    audio.diarization_result = result
    audio.save()
    
    return result
```

## 📚 Additional Resources

- **Full Documentation**: `README.md`
- **Architecture Details**: `ARCHITECTURE.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **Code Examples**: `example.py`
- **CLI Usage**: `python cli.py --help`
- **Utilities**: `utils/helpers.py`

## 🎓 Learning Path

1. **Start Here**: `test_diarization.ipynb` - Interactive tutorial
2. **Try Examples**: `example.py` - Common use cases
3. **Read Docs**: `README.md` - Complete reference
4. **Check Architecture**: `ARCHITECTURE.md` - System design
5. **Use CLI**: `cli.py` - Command-line interface
6. **Explore Utils**: `utils/helpers.py` - Helper functions

## ✨ Tips & Tricks

### Tip 1: Batch Processing

```python
from utils import batch_process_meetings

batch_process_meetings(
    audio_dir="meetings/",
    database_path="speakers.json",
    output_base_dir="results/",
    expected_language="en",
    output_transcriptions=True
)
```

### Tip 2: Extract Single Speaker

```python
from utils import extract_speaker_audio

extract_speaker_audio(
    audio_path="meeting.wav",
    segments=result['segments'],
    speaker_name="John",
    output_path="john_only.wav"
)
```

### Tip 3: Generate Timeline

```python
from utils import create_speaker_timeline

create_speaker_timeline(
    segments=result['segments'],
    output_path="timeline.png"
)
```

### Tip 4: Export to CSV

```python
from utils import export_segments_to_csv

export_segments_to_csv(
    segments=result['segments'],
    output_path="segments.csv"
)
```

### Tip 5: Speaker Statistics

```python
from utils import print_statistics

print_statistics(result['segments'])
```

## 🎉 You're Ready!

You now have everything you need to:
- ✅ Identify speakers in meetings
- ✅ Generate transcripts with speaker labels
- ✅ Process audio in any language
- ✅ Integrate with your Django/FastAPI application
- ✅ Batch process multiple files
- ✅ Export in multiple formats

Happy diarizing! 🎙️
