from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class RoomFinderUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("RoomFinder", {"fields": ("role", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("RoomFinder", {"fields": ("email", "role", "phone")}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")
