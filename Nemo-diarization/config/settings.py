# Diarization Configuration

# Model Settings
DEFAULT_DEVICE = "cuda"  # or "cpu"
SPEECHBRAIN_MODEL = "speechbrain/spkrec-ecapa-voxceleb"

# Diarization Parameters
WINDOW_SIZE = 1.5  # seconds
HOP_SIZE = 0.75  # seconds
SIMILARITY_THRESHOLD = 0.7  # for clustering
IDENTIFICATION_THRESHOLD = 0.75  # for speaker identification

# Whisper Settings
DEFAULT_WHISPER_MODEL = "base"
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large"]

# Output Settings
DEFAULT_OUTPUT_DIR = "diarization_output"
OUTPUT_FORMATS = ["json", "txt", "srt", "vtt", "rttm"]

# Audio Processing
SAMPLE_RATE = 16000  # Hz
MIN_SEGMENT_DURATION = 0.3  # seconds
MAX_MERGE_GAP = 2.0  # seconds

# Languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "fa": "Persian/Farsi",
    "ar": "Arabic",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian"
}
