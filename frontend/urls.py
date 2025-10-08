from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.main_view, name='main'),
    path('friend/<str:username>/', views.friend_page, name='friend_page'),
]
