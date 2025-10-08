from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, FriendRequest, Friendship


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'is_streaming', 'is_staff', 'date_joined')
    list_filter = ('is_streaming', 'is_staff', 'is_superuser')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Streaming Info', {'fields': ('is_streaming', 'last_seen')}),
    )


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('from_user__username', 'to_user__username')


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'created_at')
    search_fields = ('user1__username', 'user2__username')
