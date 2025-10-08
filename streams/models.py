from django.db import models
from django.conf import settings


class StreamRecording(models.Model):
    """Model for storing denoised audio recordings."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recordings'
    )
    title = models.CharField(max_length=200, blank=True)
    file = models.FileField(upload_to='recordings/')
    duration = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stream_recordings'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.owner.username} - {self.title or 'Recording'} ({self.created_at})"


class ActiveStream(models.Model):
    """Track currently active streaming sessions."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='active_stream'
    )
    session_id = models.CharField(max_length=100, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'active_streams'
    
    def __str__(self):
        return f"{self.user.username} streaming (session: {self.session_id})"
