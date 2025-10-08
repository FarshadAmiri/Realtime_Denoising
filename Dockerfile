FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1 \
    ffmpeg \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create directories for media and static files
RUN mkdir -p /app/media /app/staticfiles

# Collect static files (if needed)
# RUN python manage.py collectstatic --noinput

# Run migrations
RUN python manage.py migrate

# Expose port
EXPOSE 8000

# Run the application
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "fc25_denoise.asgi:application"]
