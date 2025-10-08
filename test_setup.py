#!/usr/bin/env python
"""
Test script to verify the Django application setup.
Run this to check if everything is configured correctly.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fc25_denoise.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from users.models import Friendship, FriendRequest
from streams.models import StreamRecording, ActiveStream

User = get_user_model()


def print_status(message, status="INFO"):
    """Print formatted status message."""
    colors = {
        "INFO": "\033[94m",  # Blue
        "SUCCESS": "\033[92m",  # Green
        "ERROR": "\033[91m",  # Red
        "WARNING": "\033[93m",  # Yellow
    }
    reset = "\033[0m"
    print(f"{colors.get(status, '')}{status}: {message}{reset}")


def test_database():
    """Test database connection and models."""
    print_status("Testing database connection...", "INFO")
    
    try:
        # Test User model
        user_count = User.objects.count()
        print_status(f"Users in database: {user_count}", "SUCCESS")
        
        # Test FriendRequest model
        fr_count = FriendRequest.objects.count()
        print_status(f"Friend requests in database: {fr_count}", "SUCCESS")
        
        # Test Friendship model
        friendship_count = Friendship.objects.count()
        print_status(f"Friendships in database: {friendship_count}", "SUCCESS")
        
        # Test StreamRecording model
        recording_count = StreamRecording.objects.count()
        print_status(f"Recordings in database: {recording_count}", "SUCCESS")
        
        # Test ActiveStream model
        active_stream_count = ActiveStream.objects.count()
        print_status(f"Active streams in database: {active_stream_count}", "SUCCESS")
        
        return True
    except Exception as e:
        print_status(f"Database test failed: {e}", "ERROR")
        return False


def test_redis():
    """Test Redis connection."""
    print_status("Testing Redis connection...", "INFO")
    
    try:
        from channels.layers import get_channel_layer
        import asyncio
        
        channel_layer = get_channel_layer()
        
        # Simple async test
        async def test_redis_async():
            await channel_layer.group_send(
                "test_group",
                {"type": "test.message", "text": "test"}
            )
            return True
        
        result = asyncio.run(test_redis_async())
        
        if result:
            print_status("Redis connection successful!", "SUCCESS")
            return True
        else:
            print_status("Redis connection failed!", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Redis test failed: {e}", "ERROR")
        print_status("Make sure Redis is running: redis-server", "WARNING")
        return False


def test_static_files():
    """Test static files configuration."""
    print_status("Testing static files...", "INFO")
    
    try:
        from django.conf import settings
        
        static_dir = settings.BASE_DIR / 'static'
        if static_dir.exists():
            print_status(f"Static directory exists: {static_dir}", "SUCCESS")
            
            # Check for key files
            files_to_check = [
                'static/css/style.css',
                'static/js/webrtc_client.js',
                'static/js/main.js',
                'static/js/friend_page.js',
            ]
            
            for file_path in files_to_check:
                full_path = settings.BASE_DIR / file_path
                if full_path.exists():
                    print_status(f"  ✓ {file_path}", "SUCCESS")
                else:
                    print_status(f"  ✗ {file_path} not found", "ERROR")
            
            return True
        else:
            print_status(f"Static directory not found: {static_dir}", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Static files test failed: {e}", "ERROR")
        return False


def test_templates():
    """Test template configuration."""
    print_status("Testing templates...", "INFO")
    
    try:
        from django.conf import settings
        
        templates_to_check = [
            'frontend/templates/frontend/base.html',
            'frontend/templates/frontend/main.html',
            'frontend/templates/frontend/friend_page.html',
            'users/templates/users/login.html',
            'users/templates/users/register.html',
        ]
        
        all_exist = True
        for template_path in templates_to_check:
            full_path = settings.BASE_DIR / template_path
            if full_path.exists():
                print_status(f"  ✓ {template_path}", "SUCCESS")
            else:
                print_status(f"  ✗ {template_path} not found", "ERROR")
                all_exist = False
        
        return all_exist
        
    except Exception as e:
        print_status(f"Templates test failed: {e}", "ERROR")
        return False


def test_urls():
    """Test URL configuration."""
    print_status("Testing URL configuration...", "INFO")
    
    try:
        from django.urls import resolve, reverse
        
        # Test some key URLs
        urls_to_test = [
            ('users:login', {}),
            ('users:register', {}),
            ('frontend:main', {}),
        ]
        
        for url_name, kwargs in urls_to_test:
            try:
                url = reverse(url_name, kwargs=kwargs)
                print_status(f"  ✓ {url_name} -> {url}", "SUCCESS")
            except Exception as e:
                print_status(f"  ✗ {url_name}: {e}", "ERROR")
        
        return True
        
    except Exception as e:
        print_status(f"URL test failed: {e}", "ERROR")
        return False


def test_apps():
    """Test installed apps."""
    print_status("Testing installed apps...", "INFO")
    
    try:
        from django.conf import settings
        
        required_apps = [
            'daphne',
            'channels',
            'rest_framework',
            'users',
            'streams',
            'frontend',
        ]
        
        installed = settings.INSTALLED_APPS
        
        for app in required_apps:
            if app in installed:
                print_status(f"  ✓ {app} is installed", "SUCCESS")
            else:
                print_status(f"  ✗ {app} is NOT installed", "ERROR")
        
        return True
        
    except Exception as e:
        print_status(f"Apps test failed: {e}", "ERROR")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Django Real-time Audio Denoising - Setup Test")
    print("="*60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Database", test_database()))
    print()
    
    results.append(("Redis", test_redis()))
    print()
    
    results.append(("Static Files", test_static_files()))
    print()
    
    results.append(("Templates", test_templates()))
    print()
    
    results.append(("URLs", test_urls()))
    print()
    
    results.append(("Apps", test_apps()))
    print()
    
    # Print summary
    print("="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        color = "\033[92m" if result else "\033[91m"
        reset = "\033[0m"
        print(f"{test_name:.<30} {color}{status}{reset}")
    
    print()
    
    # Overall result
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print_status("All tests passed! ✓", "SUCCESS")
        print_status("\nYou can now run: python manage.py runserver", "INFO")
    else:
        print_status("Some tests failed. Please fix the issues above.", "ERROR")
        sys.exit(1)


if __name__ == '__main__':
    main()
