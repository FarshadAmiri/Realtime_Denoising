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
    path('register/', user_views.register_view, name='register'),
    path('logout/', user_views.logout_view, name='logout'),
    
    # User/Friend management
    path('search/', user_views.search_users, name='search_users'),
    path('friend-requests/', user_views.friend_requests, name='friend_requests'),
    path('api/friends/request/', user_views.send_friend_request, name='send_friend_request'),
    path('api/friends/accept/', user_views.accept_friend_request, name='accept_friend_request'),
    path('api/friends/reject/', user_views.reject_friend_request, name='reject_friend_request'),
    
    # Main and user pages
    path('', stream_views.main_page, name='main_page'),
    path('user/<str:username>/', stream_views.user_page, name='user_page'),
    
    # Streaming API
    path('api/stream/start/', stream_views.start_stream, name='start_stream'),
    path('api/stream/stop/', stream_views.stop_stream, name='stop_stream'),
    path('api/stream/status/<str:username>/', stream_views.stream_status, name='stream_status'),
    path('api/recordings/', stream_views.recordings_list, name='recordings_list'),
    path('api/recordings/<str:username>/', stream_views.recordings_list, name='user_recordings_list'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
