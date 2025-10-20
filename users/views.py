from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Friendship, UserProfile


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_search_users(request):
    """JSON search endpoint for real-time search in SPA sidebar."""
    query = request.GET.get('q', '')
    results = []
    if query:
        users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)[:10]
        for user in users:
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
    return Response({'results': results})


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def undo_friend_request(request):
    """Undo (cancel) a friend request that you sent."""
    to_username = request.data.get('username')
    
    try:
        to_user = User.objects.get(username=to_username)
        friendship = Friendship.objects.get(from_user=request.user, to_user=to_user, status='pending')
        friendship.delete()
        
        return Response({'status': 'undone'})
    except (User.DoesNotExist, Friendship.DoesNotExist):
        return Response({'error': 'Friend request not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unfriend_user(request):
    """Remove an accepted friendship."""
    username = request.data.get('username')
    
    try:
        other_user = User.objects.get(username=username)
        # Find the friendship in either direction
        friendship = Friendship.objects.filter(
            Q(from_user=request.user, to_user=other_user, status='accepted') |
            Q(from_user=other_user, to_user=request.user, status='accepted')
        ).first()
        
        if not friendship:
            return Response({'error': 'Friendship not found'}, status=404)
        
        friendship.delete()
        return Response({'status': 'unfriended'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_friend_requests(request):
    """JSON endpoint providing pending friend requests (received and sent)."""
    received = Friendship.objects.filter(to_user=request.user, status='pending').select_related('from_user')
    sent = Friendship.objects.filter(from_user=request.user, status='pending').select_related('to_user')
    data = {
        'received': [r.from_user.username for r in received],
        'sent': [r.to_user.username for r in sent],
    }
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_friends_list(request):
    """List accepted friends with streaming status for SPA sidebar refresh.
    For admins, list all users instead of just friends."""
    from streams.webrtc_handler import get_session_by_username
    from streams.presence_store import is_online
    
    user = request.user
    
    # Check if user is admin
    is_admin = user.is_superuser or (hasattr(user, 'profile') and user.profile.user_level == 'admin')
    
    if is_admin:
        # Admins see all users except themselves
        users = User.objects.exclude(id=user.id).order_by('username')
        
        # Get friend IDs for marking friends in the list
        outgoing_ids = list(
            Friendship.objects.filter(from_user=user, status='accepted').values_list('to_user_id', flat=True)
        )
        incoming_ids = list(
            Friendship.objects.filter(to_user=user, status='accepted').values_list('from_user_id', flat=True)
        )
        friend_ids = set(outgoing_ids + incoming_ids)
    else:
        # Regular users see only their friends
        outgoing_ids = list(
            Friendship.objects.filter(from_user=user, status='accepted').values_list('to_user_id', flat=True)
        )
        incoming_ids = list(
            Friendship.objects.filter(to_user=user, status='accepted').values_list('from_user_id', flat=True)
        )
        friend_ids = set(outgoing_ids + incoming_ids)
        users = User.objects.filter(id__in=friend_ids)
    
    data = []
    for u in users:
        is_streaming = bool(get_session_by_username(u.username))
        user_data = {
            'username': u.username,
            'is_streaming': is_streaming,
            'is_online': is_online(u.username),
        }
        # For admins, indicate if this user is also a friend
        if is_admin:
            user_data['is_friend'] = u.id in friend_ids
        
        data.append(user_data)
    return Response({'friends': data})


# Admin Panel Views

def is_admin_user(user):
    """Check if user is admin (superuser or admin level)."""
    if user.is_superuser:
        return True
    if hasattr(user, 'profile'):
        return user.profile.user_level == 'admin'
    return False


@login_required
def admin_panel(request):
    """Admin panel page - only accessible to admins."""
    if not is_admin_user(request.user):
        return render(request, 'users/no_access.html', status=403)
    
    return render(request, 'users/admin_panel.html')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_admin_users_list(request):
    """API endpoint to get all users for admin panel."""
    if not is_admin_user(request.user):
        return Response({'error': 'Access denied'}, status=403)
    
    users = User.objects.all().select_related('profile').order_by('username')
    data = []
    for u in users:
        profile = u.profile if hasattr(u, 'profile') else None
        data.append({
            'id': u.id,
            'username': u.username,
            'name': profile.name if profile else '',
            'email': profile.email if profile else '',
            'user_level': profile.user_level if profile else 'regular',
            'allow_stream': profile.allow_stream if profile else True,
            'is_superuser': u.is_superuser,
            'date_joined': u.date_joined.isoformat() if u.date_joined else None,
        })
    return Response({'users': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_admin_create_user(request):
    """API endpoint to create a new user (admin only)."""
    if not is_admin_user(request.user):
        return Response({'error': 'Access denied'}, status=403)
    
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    name = request.data.get('name', '').strip()
    email = request.data.get('email', '').strip()
    user_level = request.data.get('user_level', 'regular')
    allow_stream = request.data.get('allow_stream', True)
    
    # Validation
    if not username:
        return Response({'error': 'Username is required'}, status=400)
    if not password:
        return Response({'error': 'Password is required'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)
    if user_level not in ['regular', 'admin']:
        return Response({'error': 'Invalid user level'}, status=400)
    
    try:
        # Create user
        user = User.objects.create_user(username=username, password=password)
        
        # Update profile
        profile = user.profile
        profile.name = name if name else None
        profile.email = email if email else None
        profile.user_level = user_level
        profile.allow_stream = allow_stream
        profile.save()
        
        return Response({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'name': profile.name,
                'email': profile.email,
                'user_level': profile.user_level,
                'allow_stream': profile.allow_stream,
            }
        }, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_admin_update_user(request, user_id):
    """API endpoint to update a user (admin only)."""
    if not is_admin_user(request.user):
        return Response({'error': 'Access denied'}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
        profile = user.profile if hasattr(user, 'profile') else None
        
        if not profile:
            return Response({'error': 'User profile not found'}, status=404)
        
        # Get data from request
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip()
        user_level = request.data.get('user_level')
        allow_stream = request.data.get('allow_stream')
        password = request.data.get('password', '').strip()
        
        # Update profile fields
        if name is not None:
            profile.name = name if name else None
        if email is not None:
            profile.email = email if email else None
        if user_level in ['regular', 'admin']:
            profile.user_level = user_level
        if allow_stream is not None:
            profile.allow_stream = bool(allow_stream)
        
        profile.save()
        
        # Update password if provided
        if password:
            user.set_password(password)
            user.save()
        
        return Response({
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'name': profile.name,
                'email': profile.email,
                'user_level': profile.user_level,
                'allow_stream': profile.allow_stream,
                'is_superuser': user.is_superuser,
            }
        })
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_admin_delete_user(request, user_id):
    """API endpoint to delete a user (admin only)."""
    if not is_admin_user(request.user):
        return Response({'error': 'Access denied'}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent deleting yourself
        if user.id == request.user.id:
            return Response({'error': 'Cannot delete yourself'}, status=400)
        
        username = user.username
        user.delete()
        
        return Response({'message': f'User {username} deleted successfully'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
