#!/usr/bin/env python
"""
Simple test script to verify Django webapp is working correctly.
Run: python test_webapp.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'audio_stream_project.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import Friendship
from streams.models import ActiveStream, StreamRecording


def test_models():
    """Test that models are working correctly."""
    print("\n=== Testing Models ===")
    
    # Test User creation
    print("\n1. Testing User model...")
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        test_user.set_password('testpass')
        test_user.save()
        print("   ✓ Created test user")
    else:
        print("   ✓ Test user already exists")
    
    # Test Friendship model
    print("\n2. Testing Friendship model...")
    alice = User.objects.filter(username='alice').first()
    bob = User.objects.filter(username='bob').first()
    
    if alice and bob:
        are_friends = Friendship.are_friends(alice, bob)
        print(f"   ✓ Alice and Bob friendship status: {are_friends}")
    else:
        print("   ℹ Alice or Bob not found (run setup to create test users)")
    
    # Test ActiveStream model
    print("\n3. Testing ActiveStream model...")
    active_count = ActiveStream.objects.count()
    print(f"   ✓ Active streams: {active_count}")
    
    # Test StreamRecording model
    print("\n4. Testing StreamRecording model...")
    recording_count = StreamRecording.objects.count()
    print(f"   ✓ Total recordings: {recording_count}")
    
    print("\n✓ All model tests passed!")
    return True


def test_audio_processor():
    """Test AudioProcessor integration."""
    print("\n=== Testing Audio Processor ===")
    
    try:
        from streams.audio_processor import AudioProcessor
        import numpy as np
        
        print("\n1. Creating AudioProcessor...")
        processor = AudioProcessor(
            session_id='test-session',
            denoise_enabled=False  # Test without denoising first
        )
        print("   ✓ AudioProcessor created")
        
        print("\n2. Testing audio chunk processing...")
        # Create dummy audio data (1 second at 48kHz)
        sample_rate = 48000
        duration = 1.0
        dummy_audio = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.1
        
        result = processor.process_audio_chunk(dummy_audio)
        if result is None:
            print("   ✓ Buffering chunk (expected for first chunk)")
        else:
            print("   ✓ Processed audio chunk")
        
        print("\n3. Testing finalization...")
        complete_audio, duration = processor.finalize()
        print(f"   ✓ Finalized recording: {len(complete_audio)} samples, {duration:.2f}s")
        
        print("\n4. Getting statistics...")
        stats = processor.get_stats()
        print(f"   ✓ Stats: {stats['chunks_processed']} chunks processed")
        
        print("\n✓ Audio processor tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Audio processor test failed: {e}")
        return False


def test_api_structure():
    """Test that API endpoints are properly configured."""
    print("\n=== Testing API Structure ===")
    
    from django.urls import resolve, reverse
    
    api_endpoints = [
        'start_stream',
        'stop_stream',
        'send_friend_request',
        'accept_friend_request',
        'reject_friend_request',
    ]
    
    print("\n1. Checking API endpoints...")
    for endpoint_name in api_endpoints:
        try:
            url = reverse(endpoint_name)
            print(f"   ✓ {endpoint_name}: {url}")
        except Exception as e:
            print(f"   ✗ {endpoint_name}: {e}")
            return False
    
    print("\n2. Checking page URLs...")
    page_endpoints = [
        ('login', []),
        ('register', []),
        ('main_page', []),
        ('search_users', []),
        ('friend_requests', []),
    ]
    
    for endpoint_name, args in page_endpoints:
        try:
            url = reverse(endpoint_name, args=args)
            print(f"   ✓ {endpoint_name}: {url}")
        except Exception as e:
            print(f"   ✗ {endpoint_name}: {e}")
            return False
    
    print("\n✓ All API structure tests passed!")
    return True


def test_websocket_routing():
    """Test WebSocket routing configuration."""
    print("\n=== Testing WebSocket Routing ===")
    
    try:
        from streams.routing import websocket_urlpatterns
        
        print("\n1. Checking WebSocket routes...")
        print(f"   ✓ Found {len(websocket_urlpatterns)} WebSocket route(s)")
        
        for pattern in websocket_urlpatterns:
            print(f"   ✓ Route: {pattern.pattern}")
        
        print("\n✓ WebSocket routing tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ WebSocket routing test failed: {e}")
        return False


def test_settings():
    """Test Django settings configuration."""
    print("\n=== Testing Django Settings ===")
    
    from django.conf import settings
    
    print("\n1. Checking installed apps...")
    required_apps = ['channels', 'rest_framework', 'users', 'streams', 'core']
    for app in required_apps:
        if app in settings.INSTALLED_APPS:
            print(f"   ✓ {app} installed")
        else:
            print(f"   ✗ {app} NOT installed")
            return False
    
    print("\n2. Checking ASGI configuration...")
    if hasattr(settings, 'ASGI_APPLICATION'):
        print(f"   ✓ ASGI_APPLICATION: {settings.ASGI_APPLICATION}")
    else:
        print("   ✗ ASGI_APPLICATION not configured")
        return False
    
    print("\n3. Checking Channel layers...")
    if hasattr(settings, 'CHANNEL_LAYERS'):
        print(f"   ✓ CHANNEL_LAYERS configured")
    else:
        print("   ✗ CHANNEL_LAYERS not configured")
        return False
    
    print("\n4. Checking audio settings...")
    audio_settings = [
        'AUDIO_CHUNK_SECONDS',
        'AUDIO_OVERLAP_SECONDS',
        'AUDIO_SAMPLE_RATE'
    ]
    for setting in audio_settings:
        if hasattr(settings, setting):
            value = getattr(settings, setting)
            print(f"   ✓ {setting}: {value}")
        else:
            print(f"   ℹ {setting} not configured (using defaults)")
    
    print("\n✓ Settings tests passed!")
    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Django WebApp Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Settings", test_settings()))
    results.append(("Models", test_models()))
    results.append(("API Structure", test_api_structure()))
    results.append(("WebSocket Routing", test_websocket_routing()))
    results.append(("Audio Processor", test_audio_processor()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name:20s} {status}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} test suites passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! The webapp is ready to use.")
        print("\nNext steps:")
        print("1. Start Redis: redis-server")
        print("2. Start Django: python manage.py runserver")
        print("   or use Daphne: daphne -b 0.0.0.0 -p 8000 audio_stream_project.asgi:application")
        print("3. Visit: http://localhost:8000")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
