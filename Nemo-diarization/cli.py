#!/usr/bin/env python
"""
Command-line interface for Nemo-Diarization
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from main import process_meeting_audio
from voice_enrollment import create_voice_database


def main():
    parser = argparse.ArgumentParser(
        description="Speaker Diarization and Transcription CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Diarization only
  python cli.py --audio meeting.wav --database speakers.json
  
  # With transcription
  python cli.py --audio meeting.wav --database speakers.json --transcribe --language en
  
  # With custom Whisper model
  python cli.py --audio meeting.wav --database speakers.json --transcribe --whisper-model whisper_medium.pt
  
  # Create speaker database
  python cli.py --create-db speakers.json --speaker John=john.wav --speaker Jane=jane1.wav,jane2.wav
        """
    )
    
    # Main arguments
    parser.add_argument(
        "--audio", "-a",
        help="Path to audio file to process"
    )
    
    parser.add_argument(
        "--database", "-d",
        help="Path to speaker database JSON file"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output directory (default: diarization_output)",
        default="diarization_output"
    )
    
    # Transcription options
    parser.add_argument(
        "--transcribe", "-t",
        action="store_true",
        help="Enable transcription"
    )
    
    parser.add_argument(
        "--language", "-l",
        help="Language code (en, fa, ar, etc.) or auto-detect if not specified"
    )
    
    parser.add_argument(
        "--whisper-model", "-w",
        help="Path to custom Whisper model"
    )
    
    parser.add_argument(
        "--num-speakers", "-n",
        type=int,
        help="Expected number of speakers"
    )
    
    # Database creation
    parser.add_argument(
        "--create-db",
        help="Create new speaker database at specified path"
    )
    
    parser.add_argument(
        "--speaker", "-s",
        action="append",
        help="Add speaker: --speaker Name=audio1.wav,audio2.wav"
    )
    
    args = parser.parse_args()
    
    # Create database mode
    if args.create_db:
        if not args.speaker:
            print("Error: --speaker required when creating database")
            parser.print_help()
            return 1
        
        # Parse speaker samples
        speaker_samples = {}
        for speaker_arg in args.speaker:
            try:
                name, paths = speaker_arg.split('=')
                audio_paths = paths.split(',')
                speaker_samples[name] = audio_paths
            except ValueError:
                print(f"Error: Invalid speaker format: {speaker_arg}")
                print("Use format: --speaker Name=audio1.wav,audio2.wav")
                return 1
        
        print(f"Creating speaker database: {args.create_db}")
        enrollment = create_voice_database(args.create_db, speaker_samples)
        print(f"✓ Database created successfully")
        return 0
    
    # Diarization mode
    if not args.audio:
        print("Error: --audio required")
        parser.print_help()
        return 1
    
    if not args.database:
        print("Error: --database required")
        parser.print_help()
        return 1
    
    # Process audio
    print(f"\nProcessing: {args.audio}")
    print(f"Database: {args.database}")
    print(f"Output: {args.output}")
    print(f"Transcription: {'enabled' if args.transcribe else 'disabled'}")
    print()
    
    result = process_meeting_audio(
        meeting_audio_path=args.audio,
        voice_embeddings_database_path=args.database,
        expected_language=args.language,
        output_transcriptions=args.transcribe,
        transcriptor_model_path=args.whisper_model,
        num_speakers=args.num_speakers,
        output_dir=args.output
    )
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Speakers detected: {result['num_speakers']}")
    print(f"Identified speakers: {result['identified_speakers']}")
    print(f"Total segments: {len(result['segments'])}")
    print(f"\nOutput files saved to: {result['output_dir']}")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
