from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Employee, Feedback, LeaveRequest, Message,Profile


# ——————————————————————————————————————
# Auth Forms
# ——————————————————————————————————————
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))


# ——————————————————————————————————————
# Employee Directory / Profile
# ——————————————————————————————————————
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["emp_id", "name", "department", "age", "salary", "years_at_company", "job_title", "location"]
        widgets = {
            "emp_id": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control"}),
            "salary": forms.NumberInput(attrs={"class": "form-control"}),
            "years_at_company": forms.NumberInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
        }

class EmployeeCreateForm(forms.ModelForm):
    # login credentials
    username = forms.CharField(max_length=150,widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        initial="employee",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Employee
        fields = ["emp_id", "name", "department", "age", "salary", "years_at_company", "job_title", "location"]
        role = forms.ChoiceField(
                choices=Profile.ROLE_CHOICES,
                initial="employee",
                help_text="Default employee",
                widget=forms.Select(attrs={"class": "form-select"})
            )
        widgets = {
            "emp_id": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control"}),
            "salary": forms.NumberInput(attrs={"class": "form-control"}),
            "years_at_company": forms.NumberInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            
        }

    def clean_username(self):
        u = self.cleaned_data["username"]
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError("Username already exists.")
        return u

    def save(self, commit=True):
        data = self.cleaned_data
        # Create user
        user = User.objects.create_user(username=data["username"], password=data["password"])
        # Ensure role on profile
        p, _ = Profile.objects.get_or_create(user=user)
        p.role = data["role"]
        p.save()

        emp: Employee = super().save(commit=False)
        emp.user = user
        if commit:
            emp.save()
        return emp


class EmployeeUpdateForm(forms.ModelForm):
    # optional password reset
    reset_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={"class": "form-control"}), help_text="Leave blank to keep current password")
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, required=False)

    class Meta:
        model = Employee
        fields = ["name", "department", "age", "salary", "years_at_company", "job_title", "location"]
        widgets = {
            "emp_id": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control"}),
            "salary": forms.NumberInput(attrs={"class": "form-control"}),
            "years_at_company": forms.NumberInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        emp: Employee = super().save(commit=False)
        if commit:
            emp.save()
            # optionally update role & password
            if emp.user:
                role = self.cleaned_data.get("role")
                if role:
                    prof, _ = Profile.objects.get_or_create(user=emp.user)
                    prof.role = role
                    prof.save()
                new_pw = self.cleaned_data.get("reset_password")
                if new_pw:
                    emp.user.set_password(new_pw)
                    emp.user.save()
        return emp

# ——————————————————————————————————————
# Feedback
# ——————————————————————————————————————
class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


# ——————————————————————————————————————
# Leave Requests
# ——————————————————————————————————————
class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ["start_date", "end_date", "reason"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


# ——————————————————————————————————————
# Messaging
# ——————————————————————————————————————
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["receiver", "subject", "body"]
        widgets = {
            "receiver": forms.Select(attrs={"class": "form-control"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


# ——————————————————————————————————————
# Bulk CSV Upload
# ——————————————————————————————————————
class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Upload CSV",
        help_text="Upload a CSV file with employee data."
    )