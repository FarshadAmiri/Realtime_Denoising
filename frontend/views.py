from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from users.models import User, Friendship
from django.db.models import Q


@login_required
def main_view(request):
    """Main page showing friends list and center content."""
    return render(request, 'frontend/main.html')


@login_required
def friend_page(request, username):
    """Friend's page showing their stream and recordings."""
    friend = get_object_or_404(User, username=username)
    
    # Check if they are friends (or viewing own page)
    if friend != request.user:
        are_friends = Friendship.objects.filter(
            Q(user1=request.user, user2=friend) |
            Q(user1=friend, user2=request.user)
        ).exists()
        
        if not are_friends:
            return render(request, 'frontend/not_friends.html', {'friend': friend})
    
    context = {
        'friend': friend,
    }
    return render(request, 'frontend/friend_page.html', context)
