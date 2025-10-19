# Admin Panel Test Script
# Run this to verify the admin panel implementation

from django.contrib.auth.models import User
from users.models import UserProfile
from django.db.models import Q

print("=" * 60)
print("ADMIN PANEL IMPLEMENTATION TEST")
print("=" * 60)

# Test 1: Check UserProfile exists for all users
print("\n1. Checking UserProfiles...")
users_without_profile = []
for user in User.objects.all():
    if not hasattr(user, 'profile'):
        users_without_profile.append(user.username)

if users_without_profile:
    print(f"   ❌ Users without profile: {users_without_profile}")
else:
    print(f"   ✓ All {User.objects.count()} users have profiles")

# Test 2: Check superusers have admin level
print("\n2. Checking superuser admin levels...")
superusers = User.objects.filter(is_superuser=True)
for su in superusers:
    if su.profile.user_level != 'admin':
        print(f"   ❌ Superuser {su.username} is not admin level")
    else:
        print(f"   ✓ Superuser {su.username} has admin level")

# Test 3: Check stream permissions
print("\n3. Checking stream permissions...")
for user in User.objects.all():
    can_stream = user.profile.can_stream()
    is_admin = user.profile.is_admin()
    allow_stream = user.profile.allow_stream
    
    if is_admin and not can_stream:
        print(f"   ❌ Admin {user.username} cannot stream (should always be able to)")
    elif not is_admin and can_stream != allow_stream:
        print(f"   ❌ User {user.username} stream permission mismatch")
    else:
        print(f"   ✓ {user.username}: admin={is_admin}, can_stream={can_stream}")

# Test 4: Summary
print("\n4. User Summary:")
print(f"   Total users: {User.objects.count()}")
print(f"   Superusers: {User.objects.filter(is_superuser=True).count()}")
print(f"   Admin level: {UserProfile.objects.filter(user_level='admin').count()}")
print(f"   Regular level: {UserProfile.objects.filter(user_level='regular').count()}")
print(f"   Can stream: {UserProfile.objects.filter(Q(user_level='admin') | Q(user__is_superuser=True) | Q(allow_stream=True)).count()}")
print(f"   Cannot stream: {UserProfile.objects.filter(user_level='regular', allow_stream=False, user__is_superuser=False).count()}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print("\nTo access admin panel:")
print("1. Log in as a superuser or admin-level user")
print("2. Navigate to: http://localhost:8000/admin-panel/")
print("3. Click 'Admin Panel' in the navbar")
