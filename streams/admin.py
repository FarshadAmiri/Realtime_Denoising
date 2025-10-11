from django.contrib import admin
from .models import ActiveStream, StreamRecording


@admin.register(ActiveStream)
class ActiveStreamAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_id', 'started_at', 'denoise_enabled']
    list_filter = ['denoise_enabled', 'started_at']
    search_fields = ['user__username']


@admin.register(StreamRecording)
class StreamRecordingAdmin(admin.ModelAdmin):
    list_display = ['owner', 'title', 'duration', 'denoise_enabled', 'created_at']
    list_filter = ['denoise_enabled', 'created_at']
    search_fields = ['owner__username', 'title']
