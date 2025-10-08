from django.urls import path
from . import views

app_name = 'streams'

urlpatterns = [
    path('api/stream/start/', views.start_stream, name='start_stream'),
    path('api/stream/stop/', views.stop_stream, name='stop_stream'),
    path('api/webrtc/offer/', views.webrtc_offer, name='webrtc_offer'),
    path('api/webrtc/listen/<str:username>/', views.listener_offer, name='listener_offer'),
    path('api/recordings/<str:username>/', views.user_recordings, name='user_recordings'),
    path('api/stream/status/<str:username>/', views.stream_status, name='stream_status'),
]
