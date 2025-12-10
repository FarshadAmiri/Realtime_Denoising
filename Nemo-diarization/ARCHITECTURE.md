# Nemo-Diarization System Architecture

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     NEMO-DIARIZATION PIPELINE                   │
└─────────────────────────────────────────────────────────────────┘

INPUT
  │
  ├── Meeting Audio (WAV/MP3/M4A/FLAC)
  └── Speaker Database (JSON)

STEP 1: LOAD SPEAKER DATABASE
  │
  ├── VoiceEnrollment.load_database()
  └── → Load speaker embeddings from JSON

STEP 2: PERFORM DIARIZATION
  │
  ├── DiarizationProcessor.extract_speaker_embeddings()
  │   ├── Sliding window analysis (1.5s windows)
  │   ├── Extract embeddings with Resemblyzer
  │   └── Generate timestamps
  │
  ├── DiarizationProcessor.cluster_speakers()
  │   ├── Compute similarity matrix
  │   ├── Agglomerative clustering
  │   └── Assign speaker labels (Speaker_0, Speaker_1, ...)
  │
  └── → Raw diarization segments

STEP 3: IDENTIFY SPEAKERS
  │
  ├── Extract audio for each segment
  ├── Generate embeddings
  ├── Compare with enrolled speakers
  │   └── Cosine similarity matching
  └── → Identified segments (John, Jane, ...)

STEP 4: TRANSCRIPTION (Optional)
  │
  ├── TranscriptionProcessor.transcribe_audio()
  │   └── Whisper model processing
  │
  ├── TranscriptionProcessor.align_transcription_with_diarization()
  │   └── Match text segments to speakers
  │
  └── → Combined segments with text

OUTPUT
  │
  ├── diarization_raw.json
  ├── diarization_identified.json
  ├── transcript.json
  ├── transcript.txt
  ├── transcript.srt
  └── transcript.vtt
```

## Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    MAIN COMPONENTS                            │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│  main.py            │  ← Entry point
│  ─────────────────  │
│  - process_meeting  │
│  - quick_diarize    │
│  - diarize_and_     │
│    transcribe       │
└──────────┬──────────┘
           │
           ├─────────────────┬─────────────────┬──────────────────┐
           │                 │                 │                  │
    ┌──────▼──────┐   ┌──────▼──────┐  ┌──────▼──────┐   ┌──────▼──────┐
    │voice_        │   │diarization_ │  │transcription│   │config/      │
    │enrollment.py │   │processor.py │  │.py          │   │settings.py  │
    │              │   │             │  │             │   │             │
    │VoiceEnrollment   │Diarization   │  │Transcription│   │Configuration│
    │              │   │Processor    │  │Processor    │   │Parameters   │
    │- enroll_     │   │             │  │             │   │             │
    │  speaker     │   │- extract_   │  │- transcribe │   │- thresholds │
    │- identify_   │   │  embeddings │  │- align_with │   │- models     │
    │  speaker     │   │- cluster_   │  │  diarization│   │- languages  │
    │- save/load_  │   │  speakers   │  │- format_    │   │             │
    │  database    │   │- identify_  │  │  transcript │   │             │
    │              │   │  speakers   │  │             │   │             │
    └──────────────┘   └──────────────┘  └──────────────┘   └──────────────┘
```

## Data Flow

```
SPEAKER ENROLLMENT
══════════════════
Reference Audio → Resemblyzer → Embeddings → JSON Database
    (WAV)          (Encoder)    (Vectors)    (speakers.json)


DIARIZATION PROCESS
═══════════════════
Meeting Audio
    │
    ├─→ [Sliding Window] → Resemblyzer → Embeddings
    │       (1.5s)          (Encoder)     (512-dim)
    │
    ├─→ [Clustering] → Speaker Segments
    │    (Sklearn)      (Speaker_0, Speaker_1, ...)
    │
    └─→ [Identification] → Named Segments
         (Cosine Sim)       (John, Jane, ...)


TRANSCRIPTION PROCESS
═════════════════════
Meeting Audio
    │
    ├─→ Whisper → Text Segments
    │   (Model)    (with timestamps)
    │
    └─→ [Alignment] → Combined Output
         (Match)       (Speaker + Text)
```

## File I/O

```
INPUT FILES
───────────
• meeting_audio.wav          (Audio to process)
• speakers.json               (Voice database)
• whisper_model.pt (optional) (Custom Whisper)

TEMPORARY FILES
───────────────
• temp_segment.wav           (During identification)

OUTPUT FILES
────────────
• diarization_raw.json       (Raw segments)
• diarization_identified.json (With speaker names)
• transcript.json            (Complete data)
• transcript.txt             (Plain text)
• transcript.srt             (SRT subtitles)
• transcript.vtt             (WebVTT subtitles)
```

## Speaker Database Format

```json
{
  "John": [0.123, -0.456, 0.789, ...],  // 512-dim embedding
  "Jane": [0.234, -0.567, 0.891, ...],
  "Ali": [0.345, -0.678, 0.912, ...]
}
```

## Segment Format

```json
{
  "start": 0.0,
  "end": 5.2,
  "speaker": "John",
  "identified": true,
  "text": "Hello everyone"  // if transcription enabled
}
```

## Model Architecture

```
SPEECHBRAIN (Speaker Recognition)
═════════════════════════════════
ECAPA-TDNN Model
  ├── Input: Audio waveform
  ├── Layers: Emphasized Channel Attention
  ├── Output: Speaker embedding (192-dim)
  └── Pre-trained on: VoxCeleb dataset

RESEMBLYZER (Speaker Verification)
══════════════════════════════════
Voice Encoder
  ├── Input: Audio waveform (16kHz)
  ├── Architecture: GE2E-based
  ├── Output: Speaker embedding (256-dim)
  └── Fast inference: ~10ms per utterance

WHISPER (Speech Recognition)
════════════════════════════
Transformer Model
  ├── Input: Audio mel-spectrogram
  ├── Encoder-Decoder architecture
  ├── Output: Text + word timestamps
  ├── Models: tiny, base, small, medium, large
  └── Languages: 90+ supported
```

## Performance Metrics

```
SPEED
─────
• Embedding extraction: ~50x real-time
• Diarization: ~10x real-time
• Transcription: ~5x real-time (base model)
• Total: ~3-5x real-time with transcription

ACCURACY
────────
• Speaker identification: 85-95% (with good samples)
• Diarization: 80-90% DER (Diarization Error Rate)
• Transcription: Depends on Whisper model & language

MEMORY
──────
• GPU: 2-4GB (with transcription)
• CPU: 4-8GB
• Models cache: ~500MB
```

## Integration Points

```
DJANGO/FASTAPI INTEGRATION
══════════════════════════

views.py / router.py
    │
    ├─→ Upload audio file
    │
    ├─→ Load speaker database
    │
    ├─→ process_meeting_audio(...)
    │
    ├─→ Return results as JSON
    │
    └─→ Serve output files

CELERY TASK (for long processing)
═════════════════════════════════

@celery.task
def process_meeting_task(audio_id):
    result = process_meeting_audio(...)
    save_to_database(result)
    notify_user()
```
