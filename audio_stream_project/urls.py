"""
URL configuration for audio_stream_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from users import views as user_views
from streams import views as stream_views
from streams import vocal_separation as vocal_views
from streams import audio_boost as boost_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('login/', user_views.login_view, name='login'),
    path('logout/', user_views.logout_view, name='logout'),
    
    # User/Friend management
    path('search/', user_views.search_users, name='search_users'),
    path('friend-requests/', user_views.friend_requests, name='friend_requests'),
    path('api/friends/request/', user_views.send_friend_request, name='send_friend_request'),
    path('api/friends/accept/', user_views.accept_friend_request, name='accept_friend_request'),
    path('api/friends/reject/', user_views.reject_friend_request, name='reject_friend_request'),
    path('api/friends/undo/', user_views.undo_friend_request, name='undo_friend_request'),
    path('api/friends/unfriend/', user_views.unfriend_user, name='unfriend_user'),
    path('api/users/search/', user_views.api_search_users, name='api_search_users'),
    path('api/friends/requests/', user_views.api_friend_requests, name='api_friend_requests'),
    path('api/friends/list/', user_views.api_friends_list, name='api_friends_list'),
    
    # Admin Panel
    path('admin-panel/', user_views.admin_panel, name='admin_panel'),
    path('api/admin/users/', user_views.api_admin_users_list, name='api_admin_users_list'),
    path('api/admin/users/create/', user_views.api_admin_create_user, name='api_admin_create_user'),
    path('api/admin/users/<int:user_id>/update/', user_views.api_admin_update_user, name='api_admin_update_user'),
    path('api/admin/users/<int:user_id>/delete/', user_views.api_admin_delete_user, name='api_admin_delete_user'),
    
    # Main and user pages
    path('', stream_views.main_page, name='main_page'),
    path('user/<str:username>/', stream_views.user_page, name='user_page'),
    
    # Streaming API
    path('api/stream/start/', stream_views.start_stream, name='start_stream'),
    path('api/stream/stop/', stream_views.stop_stream, name='stop_stream'),
    path('api/stream/status/<str:username>/', stream_views.stream_status, name='stream_status'),
    path('api/presence/heartbeat/', stream_views.heartbeat, name='presence_heartbeat'),
    path('api/stream/chunk/', stream_views.save_audio_chunk, name='save_audio_chunk'),
    path('api/stream/offer/', stream_views.webrtc_offer, name='webrtc_offer'),
    path('api/stream/listener/<str:username>/offer/', stream_views.listener_offer, name='listener_offer'),
    path('api/recordings/', stream_views.recordings_list, name='recordings_list'),
    path('api/recordings/<str:username>/', stream_views.recordings_list, name='user_recordings_list'),
    path('api/recordings/<int:recording_id>/delete/', stream_views.delete_recording, name='delete_recording'),
    path('api/recordings/<int:recording_id>/rename/', stream_views.rename_recording, name='rename_recording'),
    
    # File denoising
    path('api/denoise/upload/', stream_views.upload_audio_file, name='upload_audio_file'),
    path('api/denoise/files/', stream_views.list_uploaded_files, name='list_uploaded_files'),
    path('api/denoise/files/<int:file_id>/status/', stream_views.get_file_status, name='get_file_status'),
    path('api/denoise/files/<int:file_id>/delete/', stream_views.delete_uploaded_file, name='delete_uploaded_file'),
    
    # Vocal separation
    path('api/vocal/separate/', vocal_views.upload_vocal_file, name='upload_vocal_file'),
    path('api/vocal/files/', vocal_views.list_vocal_files, name='list_vocal_files'),
    path('api/vocal/files/<int:file_id>/status/', vocal_views.get_vocal_file_status, name='get_vocal_file_status'),
    path('api/vocal/files/<int:file_id>/delete/', vocal_views.delete_vocal_file, name='delete_vocal_file'),
    
    # Audio boost
    path('api/boost/upload/', boost_views.upload_boost_file, name='upload_boost_file'),
    path('api/boost/files/', boost_views.list_boost_files, name='list_boost_files'),
    path('api/boost/files/<int:file_id>/status/', boost_views.get_boost_file_status, name='get_boost_file_status'),
    path('api/boost/files/<int:file_id>/delete/', boost_views.delete_boost_file, name='delete_boost_file'),
    
    # Speaker extraction
    path('api/speaker/extract/', stream_views.upload_speaker_extraction, name='upload_speaker_extraction'),
    path('api/speaker/files/', stream_views.list_speaker_extraction_files, name='list_speaker_extraction_files'),
    path('api/speaker/files/<int:file_id>/delete/', stream_views.delete_speaker_extraction_file, name='delete_speaker_extraction_file'),
    
    # Voice cloning
    path('api/voiceclone/convert/', stream_views.upload_voice_clone, name='upload_voice_clone'),
    path('api/voiceclone/files/', stream_views.list_voice_clone_files, name='list_voice_clone_files'),
    path('api/voiceclone/files/<int:file_id>/delete/', stream_views.delete_voice_clone_file, name='delete_voice_clone_file'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Don't add static() for STATIC_URL - Django's staticfiles app handles it automatically
