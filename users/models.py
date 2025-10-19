from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile with additional fields."""
    USER_LEVEL_CHOICES = [
        ('regular', 'Regular'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    user_level = models.CharField(max_length=10, choices=USER_LEVEL_CHOICES, default='regular')
    allow_stream = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.user_level}"
    
    def is_admin(self):
        """Check if user is admin (either superuser or admin level)."""
        return self.user.is_superuser or self.user_level == 'admin'
    
    def can_stream(self):
        """Check if user is allowed to stream."""
        # Admins and superusers can always stream
        if self.user.is_superuser or self.user_level == 'admin':
            return True
        return self.allow_stream


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created."""
    if created:
        # Superusers get admin level automatically
        user_level = 'admin' if instance.is_superuser else 'regular'
        UserProfile.objects.create(user=instance, user_level=user_level)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Friendship(models.Model):
    """Represents a mutual friendship between two users."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    from_user = models.ForeignKey(User, related_name='friendships_sent', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='friendships_received', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"
    
    @classmethod
    def are_friends(cls, user1, user2):
        """Check if two users are friends (mutual accepted friendship)."""
        return cls.objects.filter(
            models.Q(from_user=user1, to_user=user2, status='accepted') |
            models.Q(from_user=user2, to_user=user1, status='accepted')
        ).exists()
