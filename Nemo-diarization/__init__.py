"""
Nemo-Diarization: Speaker Diarization and Identification System
Uses SpeechBrain for diarization and Resemblyzer for speaker identification
"""

try:
    from .main import process_meeting_audio
except ImportError:
    from main import process_meeting_audio

__version__ = "1.0.0"
__all__ = ["process_meeting_audio"]
