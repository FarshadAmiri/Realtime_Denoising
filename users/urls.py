from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Auth views
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # API endpoints
    path('api/search/', views.search_users, name='search_users'),
    path('api/friends/', views.get_friends, name='get_friends'),
    path('api/friend-request/send/', views.send_friend_request, name='send_friend_request'),
    path('api/friend-request/<int:request_id>/respond/', views.respond_friend_request, name='respond_friend_request'),
    path('api/friend-requests/pending/', views.get_pending_requests, name='pending_requests'),
]
