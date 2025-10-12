from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Friendship


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('main_page')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('main_page')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'users/login.html')


def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('main_page')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password != password2:
            messages.error(request, 'Passwords do not match')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect('main_page')
    
    return render(request, 'users/register.html')


def logout_view(request):
    """User logout view."""
    logout(request)
    return redirect('login')


@login_required
def search_users(request):
    """Search for users to add as friends."""
    query = request.GET.get('q', '')
    results = []
    
    if query:
        users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)[:10]
        
        for user in users:
            # Check friendship status
            sent_request = Friendship.objects.filter(from_user=request.user, to_user=user).first()
            received_request = Friendship.objects.filter(from_user=user, to_user=request.user).first()
            
            status = 'none'
            if sent_request:
                status = f'sent_{sent_request.status}'
            elif received_request:
                status = f'received_{received_request.status}'
            
            results.append({
                'username': user.username,
                'friendship_status': status,
            })
    
    return render(request, 'users/search.html', {
        'query': query,
        'results': results,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request):
    """Send a friend request."""
    to_username = request.data.get('username')
    
    try:
        to_user = User.objects.get(username=to_username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    if to_user == request.user:
        return Response({'error': 'Cannot send friend request to yourself'}, status=400)
    
    # Check if friendship already exists
    existing = Friendship.objects.filter(
        Q(from_user=request.user, to_user=to_user) |
        Q(from_user=to_user, to_user=request.user)
    ).first()
    
    if existing:
        return Response({'error': 'Friend request already exists'}, status=400)
    
    # Create friend request
    Friendship.objects.create(from_user=request.user, to_user=to_user, status='pending')
    
    return Response({'status': 'sent'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_friend_request(request):
    """Accept a friend request."""
    from_username = request.data.get('username')
    
    try:
        from_user = User.objects.get(username=from_username)
        friendship = Friendship.objects.get(from_user=from_user, to_user=request.user, status='pending')
        friendship.status = 'accepted'
        friendship.save()
        
        return Response({'status': 'accepted'})
    except (User.DoesNotExist, Friendship.DoesNotExist):
        return Response({'error': 'Friend request not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_friend_request(request):
    """Reject a friend request."""
    from_username = request.data.get('username')
    
    try:
        from_user = User.objects.get(username=from_username)
        friendship = Friendship.objects.get(from_user=from_user, to_user=request.user, status='pending')
        friendship.delete()
        
        return Response({'status': 'rejected'})
    except (User.DoesNotExist, Friendship.DoesNotExist):
        return Response({'error': 'Friend request not found'}, status=404)


@login_required
def friend_requests(request):
    """View pending friend requests."""
    # Received requests
    received = Friendship.objects.filter(to_user=request.user, status='pending').select_related('from_user')
    
    # Sent requests
    sent = Friendship.objects.filter(from_user=request.user, status='pending').select_related('to_user')
    
    return render(request, 'users/friend_requests.html', {
        'received_requests': received,
        'sent_requests': sent,
    })
