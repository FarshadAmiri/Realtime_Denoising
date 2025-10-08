from django.contrib import admin
from .models import StreamRecording, ActiveStream


@admin.register(StreamRecording)
class StreamRecordingAdmin(admin.ModelAdmin):
    list_display = ('owner', 'title', 'duration', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('owner__username', 'title')
    readonly_fields = ('created_at',)


@admin.register(ActiveStream)
class ActiveStreamAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_id', 'started_at')
    readonly_fields = ('started_at',)
