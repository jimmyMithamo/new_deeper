# Register your models here.
from django.contrib import admin
from .models import Member, Group, leaders, Session, Attendance  # Import your models

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "email", "group")

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "leader")

@admin.register(leaders)
class LeadersAdmin(admin.ModelAdmin):
    list_display = ("name", "username", "group")

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("name", "date", "created_at")

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("member", "session", "status", "submitted")
