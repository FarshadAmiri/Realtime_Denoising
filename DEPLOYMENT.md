# Deployment Guide

This guide covers deploying the real-time audio denoising web application to production.

## Production Checklist

### Before Deployment

- [ ] Set `DEBUG=False` in settings
- [ ] Configure proper `SECRET_KEY` (generate a new one)
- [ ] Set `ALLOWED_HOSTS` to your domain(s)
- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure Redis with authentication
- [ ] Set up static file serving (nginx or whitenoise)
- [ ] Configure media file storage
- [ ] Set up SSL/TLS certificates
- [ ] Configure logging
- [ ] Set up monitoring and alerting
- [ ] Create backup strategy
- [ ] Test WebSocket connections work

## Environment Setup

### 1. Server Requirements

**Minimum:**
- 4 CPU cores
- 8 GB RAM
- 50 GB storage
- Ubuntu 20.04 or later

**Recommended:**
- 8+ CPU cores
- 16+ GB RAM
- NVIDIA GPU (for faster denoising)
- 100+ GB storage

### 2. Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip
sudo apt install -y redis-server nginx supervisor

# Install CUDA (if using GPU)
# Follow NVIDIA CUDA installation guide for your system
```

### 3. Create Application User

```bash
# Create user
sudo useradd -m -s /bin/bash audiostream
sudo usermod -aG www-data audiostream

# Switch to user
sudo su - audiostream
```

### 4. Clone and Setup Application

```bash
# Clone repository
cd /home/audiostream
git clone https://github.com/FarshadAmiri/Realtime_Denoising.git
cd Realtime_Denoising

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn whitenoise psycopg2-binary
```

### 5. Configure Environment

```bash
# Create .env file
cat > .env << EOF
DEBUG=False
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://audiostream_user:password@localhost:5432/audiostream_db

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Audio settings
AUDIO_CHUNK_SECONDS=2.0
AUDIO_OVERLAP_SECONDS=0.5
AUDIO_SAMPLE_RATE=48000
EOF
```

### 6. Configure Django Settings for Production

Update `audio_stream_project/settings.py`:

```python
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

# Security
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600
    )
}

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_ROOT = BASE_DIR / 'media'

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Redis with password
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(
                os.getenv('REDIS_HOST', '127.0.0.1'),
                int(os.getenv('REDIS_PORT', 6379))
            )],
            "password": os.getenv('REDIS_PASSWORD'),
        },
    },
}
```

## Database Setup

### PostgreSQL Installation

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE audiostream_db;
CREATE USER audiostream_user WITH PASSWORD 'secure_password_here';
ALTER ROLE audiostream_user SET client_encoding TO 'utf8';
ALTER ROLE audiostream_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE audiostream_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE audiostream_db TO audiostream_user;
\q
EOF
```

### Run Migrations

```bash
cd /home/audiostream/Realtime_Denoising
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## Redis Configuration

### Secure Redis

```bash
# Edit Redis config
sudo nano /etc/redis/redis.conf

# Add/modify these lines:
bind 127.0.0.1
requirepass your_redis_password_here
maxmemory 512mb
maxmemory-policy allkeys-lru

# Restart Redis
sudo systemctl restart redis
sudo systemctl enable redis

# Test
redis-cli -a your_redis_password_here ping
```

## Web Server Setup

### Supervisor for Process Management

Create `/etc/supervisor/conf.d/audiostream.conf`:

```ini
[program:audiostream-daphne]
command=/home/audiostream/Realtime_Denoising/venv/bin/daphne -b 127.0.0.1 -p 8000 audio_stream_project.asgi:application
directory=/home/audiostream/Realtime_Denoising
user=audiostream
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/audiostream/daphne.log
environment=PATH="/home/audiostream/Realtime_Denoising/venv/bin"

[program:audiostream-worker]
command=/home/audiostream/Realtime_Denoising/venv/bin/python manage.py runworker
directory=/home/audiostream/Realtime_Denoising
user=audiostream
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/audiostream/worker.log
numprocs=2
process_name=%(program_name)s_%(process_num)02d
```

```bash
# Create log directory
sudo mkdir -p /var/log/audiostream
sudo chown audiostream:audiostream /var/log/audiostream

# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

### Nginx Configuration

Create `/etc/nginx/sites-available/audiostream`:

```nginx
upstream audiostream {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;

    # Static files
    location /static/ {
        alias /home/audiostream/Realtime_Denoising/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /home/audiostream/Realtime_Denoising/media/;
        expires 7d;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://audiostream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # Django application
    location / {
        proxy_pass http://audiostream;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/audiostream /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is configured automatically
```

## Monitoring and Logging

### Application Logging

Update `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/audiostream/django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

### System Monitoring

```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Monitor Redis
redis-cli -a your_password info stats

# Monitor Supervisor
sudo supervisorctl status

# View logs
tail -f /var/log/audiostream/daphne.log
tail -f /var/log/audiostream/worker.log
tail -f /var/log/nginx/error.log
```

## Backup Strategy

### Database Backup

```bash
# Create backup script
cat > /home/audiostream/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/audiostream/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
pg_dump -U audiostream_user audiostream_db > $BACKUP_DIR/db_$TIMESTAMP.sql
gzip $BACKUP_DIR/db_$TIMESTAMP.sql
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /home/audiostream/backup_db.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /home/audiostream/backup_db.sh
```

### Media Files Backup

```bash
# Rsync to backup server
rsync -avz /home/audiostream/Realtime_Denoising/media/ backup-server:/backups/audiostream/media/
```

## Performance Optimization

### Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_friendship_users ON users_friendship(from_user_id, to_user_id);
CREATE INDEX idx_active_stream_user ON streams_activestream(user_id);
CREATE INDEX idx_recording_owner ON streams_streamrecording(owner_id);
CREATE INDEX idx_recording_created ON streams_streamrecording(created_at);
```

### Redis Optimization

```bash
# In redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
save ""  # Disable persistence for speed (if acceptable)
```

### Application Optimization

```python
# In views.py, use select_related and prefetch_related
friendships = Friendship.objects.filter(
    Q(from_user=request.user, status='accepted') |
    Q(to_user=request.user, status='accepted')
).select_related('from_user', 'to_user')

recordings = StreamRecording.objects.filter(
    owner=target_user
).select_related('owner')[:20]  # Limit results
```

## Security Hardening

### Firewall Configuration

```bash
# UFW firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Fail2ban

```bash
# Install fail2ban
sudo apt install -y fail2ban

# Configure for nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Edit /etc/fail2ban/jail.local
[nginx-http-auth]
enabled = true

[nginx-noscript]
enabled = true

sudo systemctl restart fail2ban
```

### Regular Updates

```bash
# Create update script
cat > /home/audiostream/update.sh << 'EOF'
#!/bin/bash
cd /home/audiostream/Realtime_Denoising
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
python manage.py migrate
python manage.py collectstatic --noinput
sudo supervisorctl restart all
EOF

chmod +x /home/audiostream/update.sh
```

## Troubleshooting

### Check Service Status

```bash
# Supervisor
sudo supervisorctl status

# Nginx
sudo systemctl status nginx

# Redis
sudo systemctl status redis

# PostgreSQL
sudo systemctl status postgresql
```

### Common Issues

**WebSocket not connecting:**
- Check Nginx WebSocket proxy configuration
- Verify Redis is running and accessible
- Check firewall rules

**Static files not loading:**
- Run `python manage.py collectstatic`
- Check Nginx static file configuration
- Verify file permissions

**Database connection errors:**
- Check PostgreSQL is running
- Verify database credentials in .env
- Check PostgreSQL logs: `sudo tail -f /var/log/postgresql/postgresql-*.log`

## Scaling

### Horizontal Scaling

1. **Load Balancer**: Add multiple application servers behind nginx load balancer
2. **Redis Sentinel**: High availability Redis setup
3. **PostgreSQL Replication**: Master-slave database setup
4. **CDN**: Use CloudFlare or similar for static/media files

### Vertical Scaling

1. Increase server resources (CPU, RAM)
2. Add GPU for faster denoising
3. Use Redis Cluster for distributed caching
4. Optimize database queries and add indexes

## Monitoring Services

Consider using:
- **Sentry**: Error tracking
- **New Relic**: Application performance monitoring
- **Prometheus + Grafana**: Metrics and dashboards
- **ELK Stack**: Log aggregation and analysis

## Support

For deployment issues:
1. Check application logs
2. Review nginx error logs
3. Test Redis connection
4. Verify database connectivity
5. Open an issue on GitHub with details
