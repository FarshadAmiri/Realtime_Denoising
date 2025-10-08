#!/usr/bin/env python
"""
Setup script for creating demo users for testing the application.
Run this after migrations: python setup_demo.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fc25_denoise.settings')
django.setup()

from users.models import User, FriendRequest, Friendship


def create_demo_users():
    """Create demo users and friendships for testing."""
    print("Creating demo users...")
    
    # Create users
    users_data = [
        {'username': 'alice', 'password': 'demo123'},
        {'username': 'bob', 'password': 'demo123'},
        {'username': 'charlie', 'password': 'demo123'},
    ]
    
    users = {}
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={'is_active': True}
        )
        if created:
            user.set_password(user_data['password'])
            user.save()
            print(f"  Created user: {user.username}")
        else:
            print(f"  User already exists: {user.username}")
        users[user.username] = user
    
    # Create friendships
    print("\nCreating friendships...")
    friendships = [
        ('alice', 'bob'),
        ('alice', 'charlie'),
    ]
    
    for user1_name, user2_name in friendships:
        user1 = users[user1_name]
        user2 = users[user2_name]
        
        friendship, created = Friendship.objects.get_or_create(
            user1=user1,
            user2=user2
        )
        if created:
            print(f"  Created friendship: {user1_name} <-> {user2_name}")
        else:
            print(f"  Friendship already exists: {user1_name} <-> {user2_name}")
    
    print("\nDemo setup complete!")
    print("\nYou can now login with:")
    print("  Username: alice, Password: demo123")
    print("  Username: bob, Password: demo123")
    print("  Username: charlie, Password: demo123")


if __name__ == '__main__':
    create_demo_users()
