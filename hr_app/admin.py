from django.contrib import admin
from .models import Profile, Employee, Prediction, Feedback, Message, LeaveRequest

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username",)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("emp_id", "name", "department", "age", "years_at_company", "salary")
    list_filter = ("department",)
    search_fields = ("emp_id", "name", "department")

@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("employee", "kind", "result", "probability", "created_at")
    list_filter = ("kind",)
    search_fields = ("employee__emp_id", "employee__name")

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("employee", "sentiment", "created_at")
    list_filter = ("sentiment",)
    search_fields = ("employee__emp_id", "employee__name", "text")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "receiver", "subject", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("sender__username", "receiver__username", "subject", "body")

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "start_date", "end_date", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("employee__emp_id", "employee__name", "reason")
