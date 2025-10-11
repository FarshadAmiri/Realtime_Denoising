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
    
    def __str__(self):
        return f"{self.owner.username} - {self.title} ({self.duration}s)"
    
    def get_duration_display(self):
        """Return duration in mm:ss format."""
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes:02d}:{seconds:02d}"
