#!/bin/bash
# Quick start script for Real-time Audio Denoising Web Application

set -e

echo "==========================================="
echo "Audio Streaming WebApp - Quick Start"
echo "==========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version found"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install minimal dependencies for quick testing
echo "Installing minimal dependencies..."
pip install -q Django channels channels-redis djangorestframework django-cors-headers daphne redis python-dotenv
echo "✓ Dependencies installed"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi
echo ""

# Run migrations if needed
if [ ! -f "db.sqlite3" ]; then
    echo "Setting up database..."
    python manage.py migrate --no-input
    echo "✓ Database initialized"
    
    echo ""
    echo "Creating test users..."
    python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from users.models import Friendship

# Create admin
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
    print("  ✓ Created admin user (username: admin, password: admin123)")

# Create test users
if not User.objects.filter(username='alice').exists():
    User.objects.create_user('alice', 'alice@test.com', 'password123')
    print("  ✓ Created user: alice (password: password123)")
    
if not User.objects.filter(username='bob').exists():
    User.objects.create_user('bob', 'bob@test.com', 'password123')
    print("  ✓ Created user: bob (password: password123)")

# Create friendship
alice = User.objects.get(username='alice')
bob = User.objects.get(username='bob')

if not Friendship.objects.filter(from_user=alice, to_user=bob).exists() and not Friendship.objects.filter(from_user=bob, to_user=alice).exists():
    Friendship.objects.create(from_user=alice, to_user=bob, status='accepted')
    print("  ✓ Alice and Bob are now friends")
EOF
else
    echo "✓ Database already exists"
fi
echo ""

# Check Redis
echo "Checking Redis..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis is running"
else
    echo "⚠️  Redis is not running!"
    echo "   Please start Redis in another terminal:"
    echo "   $ redis-server"
    echo ""
    echo "   Or install Redis:"
    echo "   Ubuntu/Debian: sudo apt install redis-server"
    echo "   macOS: brew install redis"
    echo ""
fi

# Run tests
echo "Running basic tests..."
python test_webapp.py > /tmp/test_output.txt 2>&1
if grep -q "All tests passed" /tmp/test_output.txt; then
    echo "✓ Tests passed"
else
    echo "⚠️  Some tests failed (see test_webapp.py for details)"
fi
echo ""

echo "==========================================="
echo "Setup complete! 🎉"
echo "==========================================="
echo ""
echo "Quick Reference:"
echo "  Admin user:  username=admin, password=admin123"
echo "  Test users:  alice/password123, bob/password123"
echo ""
echo "To start the application:"
echo "  1. Make sure Redis is running: redis-server"
echo "  2. Start Django: python manage.py runserver"
echo "     OR use Daphne: daphne -b 0.0.0.0 -p 8000 audio_stream_project.asgi:application"
echo "  3. Visit: http://localhost:8000"
echo ""
echo "Documentation:"
echo "  README.md              - Project overview"
echo "  USAGE_GUIDE.md         - How to use the app"
echo "  DEPLOYMENT.md          - Production deployment"
echo "  IMPLEMENTATION_SUMMARY.md - Technical details"
echo ""
echo "Happy streaming! 🎙️"
echo ""
