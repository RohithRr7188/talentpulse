from django.db import models
from django.conf import settings
from django.utils import timezone

# ——————————————————————————————————————————
# Roles / Profile
# ——————————————————————————————————————————
class Profile(models.Model):
    ROLE_CHOICES = (
        ("employee", "Employee"),
        ("hr", "HR / Admin"),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default="employee")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_hr(self) -> bool:
        # Treat either explicit role or is_staff as HR
        return self.role == "hr" or getattr(self.user, "is_staff", False)


# ——————————————————————————————————————————
# Core Employee entity
# ——————————————————————————————————————————
class Employee(models.Model):
    # Optional linkage to a user login (some employees may not have accounts)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="employee"
    )
    emp_id = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=120, db_index=True)
    department = models.CharField(max_length=80, db_index=True)
    age = models.PositiveIntegerField()
    salary = models.FloatField()
    years_at_company = models.FloatField()
    date_joined = models.DateField(null=True, blank=True)

    # Optional metadata for directory/search
    job_title = models.CharField(max_length=120, blank=True, default="")
    location = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["department"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.emp_id} — {self.name}"


# ——————————————————————————————————————————
# Predictions (Retention / Promotion / etc.)
# ——————————————————————————————————————————
class Prediction(models.Model):
    PREDICTION_KIND = (
        ("retention", "Retention"),
        ("promotion", "Promotion"),
        ("engagement", "Engagement"),
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="predictions")
    kind = models.CharField(max_length=20, choices=PREDICTION_KIND)
    result = models.CharField(max_length=20)     # "0"/"1" or label text
    probability = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind", "created_at"]),
        ]

    def __str__(self):
        return f"{self.employee.emp_id} {self.kind}={self.result} ({self.probability})"


# ——————————————————————————————————————————
# Feedback + Sentiment
# ——————————————————————————————————————————
class Feedback(models.Model):
    SENTIMENT = (
        ("Positive", "Positive"),
        ("Neutral", "Neutral"),
        ("Negative", "Negative"),
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="feedbacks")
    text = models.TextField()
    sentiment = models.CharField(max_length=12, choices=SENTIMENT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback({self.employee.emp_id}, {self.sentiment})"


# ——————————————————————————————————————————
# Internal Messaging
# ——————————————————————————————————————————
class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    subject = models.CharField(max_length=120)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Msg {self.id} {self.sender}→{self.receiver}: {self.subject[:25]}"


# ——————————————————————————————————————————
# Leave Management
# ——————————————————————————————————————————
class LeaveRequest(models.Model):
    STATUS = (
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS, default="Pending")
    hr_comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Leave({self.employee.emp_id} {self.start_date}→{self.end_date} {self.status})"

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def clean(self):
        # Optional sanity checks
        if self.end_date < self.start_date:
            from django.core.exceptions import ValidationError
            raise ValidationError("End date cannot be before start date.")
        if self.start_date < timezone.now().date() and self.status == "Pending":
            # Allow backdated requests if you want; this just warns in admin
            pass
