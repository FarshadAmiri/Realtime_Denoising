from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import User, FriendRequest, Friendship


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    """Search for users by username."""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return Response({'users': []})
    
    users = User.objects.filter(
        username__icontains=query
    ).exclude(
        id=request.user.id
    )[:10]
    
    data = [{
        'username': user.username,
        'id': user.id,
        'is_streaming': user.is_streaming,
    } for user in users]
    
    return Response({'users': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request):
    """Send a friend request to another user."""
    to_username = request.data.get('username')
    
    if not to_username:
        return Response(
            {'error': 'Username required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        to_user = User.objects.get(username=to_username)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if to_user == request.user:
        return Response(
            {'error': 'Cannot send friend request to yourself'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already friends
    are_friends = Friendship.objects.filter(
        Q(user1=request.user, user2=to_user) |
        Q(user1=to_user, user2=request.user)
    ).exists()
    
    if are_friends:
        return Response(
            {'error': 'Already friends'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if request already exists
    existing_request = FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=to_user) |
        Q(from_user=to_user, to_user=request.user)
    ).first()
    
    if existing_request:
        return Response(
            {'error': 'Friend request already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create friend request
    friend_request = FriendRequest.objects.create(
        from_user=request.user,
        to_user=to_user
    )
    
    return Response({
        'message': 'Friend request sent',
        'request_id': friend_request.id
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_friend_request(request, request_id):
    """Accept or reject a friend request."""
    action = request.data.get('action')  # 'accept' or 'reject'
    
    if action not in ['accept', 'reject']:
        return Response(
            {'error': 'Invalid action'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        friend_request = FriendRequest.objects.get(
            id=request_id,
            to_user=request.user,
            status='pending'
        )
    except FriendRequest.DoesNotExist:
        return Response(
            {'error': 'Friend request not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if action == 'accept':
        # Create friendship (bidirectional)
        Friendship.objects.create(
            user1=friend_request.from_user,
            user2=friend_request.to_user
        )
        friend_request.status = 'accepted'
        friend_request.save()
        
        return Response({'message': 'Friend request accepted'})
    else:
        friend_request.status = 'rejected'
        friend_request.save()
        
        return Response({'message': 'Friend request rejected'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_friends(request):
    """Get list of user's friends."""
    user = request.user
    
    # Get all friendships
    friendships = Friendship.objects.filter(
        Q(user1=user) | Q(user2=user)
    ).select_related('user1', 'user2')
    
    friends = []
    for friendship in friendships:
        friend = friendship.user2 if friendship.user1 == user else friendship.user1
        friends.append({
            'username': friend.username,
            'id': friend.id,
            'is_streaming': friend.is_streaming,
        })
    
    return Response({'friends': friends})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_requests(request):
    """Get pending friend requests (sent and received)."""
    user = request.user
    
    sent_requests = FriendRequest.objects.filter(
        from_user=user,
        status='pending'
    ).select_related('to_user')
    
    received_requests = FriendRequest.objects.filter(
        to_user=user,
        status='pending'
    ).select_related('from_user')
    
    sent_data = [{
        'id': req.id,
        'to_user': req.to_user.username,
        'created_at': req.created_at.isoformat(),
    } for req in sent_requests]
    
    received_data = [{
        'id': req.id,
        'from_user': req.from_user.username,
        'created_at': req.created_at.isoformat(),
    } for req in received_requests]
    
    return Response({
        'sent': sent_data,
        'received': received_data
    })


# Regular Django views for templates
def login_view(request):
    """Login page."""
    if request.user.is_authenticated:
        return redirect('frontend:main')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('frontend:main')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'users/login.html')


def register_view(request):
    """Registration page."""
    if request.user.is_authenticated:
        return redirect('frontend:main')
    
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
            return redirect('frontend:main')
    
    return render(request, 'users/register.html')


@login_required
def logout_view(request):
    """Logout user."""
    logout(request)
    return redirect('users:login')
