from django.db import models
from django.contrib.auth.models import User
import uuid


class ActiveStream(models.Model):
    """Tracks currently active audio streams."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='active_stream')
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    denoise_enabled = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.username} streaming (session: {self.session_id})"


class StreamRecording(models.Model):
    """Stores completed audio stream recordings."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recordings')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='recordings/')
    duration = models.FloatField(default=0.0)  # Duration in seconds
    denoise_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']


class UploadedAudioFile(models.Model):
    """Stores user-uploaded audio files for denoising."""
    PROCESSING_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    BOOST_LEVEL = [
        ('none', 'No Boost'),
        ('2x', '2x Volume'),
        ('3x', '3x Volume'),
        ('4x', '4x Volume'),
        ('5x', '5x Volume'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files')
    original_filename = models.CharField(max_length=255)
    original_file = models.FileField(upload_to='uploads/original/')
    denoised_file = models.FileField(upload_to='uploads/denoised/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='pending')
    boost_level = models.CharField(max_length=10, choices=BOOST_LEVEL, default='none')
    error_message = models.TextField(null=True, blank=True)
    duration = models.FloatField(default=0.0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.owner.username} - {self.original_filename} ({self.status})"
    
    def get_duration_display(self):
        """Return duration in mm:ss format."""
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes:02d}:{seconds:02d}"


class VocalSeparationFile(models.Model):
    """Stores user-uploaded audio files for vocal separation using Demucs."""
    PROCESSING_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vocal_separation_files')
    original_filename = models.CharField(max_length=255)
    original_file = models.FileField(upload_to='uploads/vocal_separation/original/')
    vocals_file = models.FileField(upload_to='uploads/vocal_separation/vocals/', null=True, blank=True)
    instrumental_file = models.FileField(upload_to='uploads/vocal_separation/instrumental/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='pending')
    error_message = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.owner.username} - {self.original_filename} ({self.status})"


class AudioBoostFile(models.Model):
    """Stores user-uploaded audio files for volume boost/normalization."""
    PROCESSING_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]
    
    BOOST_LEVEL = [
        ('gentle', 'Gentle'),
        ('medium', 'Medium'),
        ('strong', 'Strong'),
        ('max', 'Maximum'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audio_boost_files')
    original_filename = models.CharField(max_length=255)
    original_file = models.FileField(upload_to='uploads/audio_boost/original/')
    boosted_file = models.FileField(upload_to='uploads/audio_boost/boosted/', null=True, blank=True)
    boost_level = models.CharField(max_length=20, choices=BOOST_LEVEL, default='medium')
    status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='pending')
    error_message = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.owner.username} - {self.original_filename} ({self.boost_level}/{self.status})"
