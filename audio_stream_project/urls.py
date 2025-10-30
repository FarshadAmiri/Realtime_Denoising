"""
URL configuration for audio_stream_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from users import views as user_views
from streams import views as stream_views

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
    
    # File denoising
    path('api/denoise/upload/', stream_views.upload_audio_file, name='upload_audio_file'),
    path('api/denoise/files/', stream_views.list_uploaded_files, name='list_uploaded_files'),
    path('api/denoise/files/<int:file_id>/status/', stream_views.get_file_status, name='get_file_status'),
    path('api/denoise/files/<int:file_id>/delete/', stream_views.delete_uploaded_file, name='delete_uploaded_file'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
