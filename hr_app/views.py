import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg
from django.http import HttpResponse
import pandas as pd
import joblib, os
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib.auth.models import User
from textblob import TextBlob

from .forms import (
    UserRegisterForm, UserLoginForm, EmployeeForm, FeedbackForm,
    LeaveRequestForm, MessageForm, CSVUploadForm
)
from .models import Employee, Feedback, LeaveRequest, Message, Prediction
import joblib, pandas as pd
from pathlib import Path
from .forms import EmployeeCreateForm, EmployeeUpdateForm

@login_required
def role_redirect(request):
    if hasattr(request.user, "profile") and request.user.profile.is_hr:
        return redirect("hr_dashboard")
    return redirect("employee_dashboard")

PROMOTION_MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml","models", "promotion.pkl")
promotion_model = joblib.load(PROMOTION_MODEL_PATH)

def promotion_predict(data: dict):
    """
    Run promotion prediction using trained model.
    """
    df = pd.DataFrame([data])
    yhat = promotion_model.predict(df)[0]
    prob = promotion_model.predict_proba(df)[0][1]
    return ("Eligible" if yhat == 1 else "Not Eligible", round(prob * 100, 2))


BASE = Path(__file__).resolve().parent
_promotion = None
_retention = None

def load_models():
    global _promotion, _retention
    if _promotion is None:
        _promotion = joblib.load(BASE / "ml" / "models" / "promotion.pkl")
    if _retention is None:
        _retention = joblib.load(BASE / "ml" / "models" / "retention.pkl")

@login_required
def csv_predict_upload(request):
    predictions = []

    if request.method == "POST":
        if "csv_file" not in request.FILES:
            messages.error(request, "Please upload a CSV file.")
            return redirect("csv_predict_upload")

        df = pd.read_csv(request.FILES["csv_file"])
        load_models()

        for _, row in df.iterrows():
            # Retention
            r_pred, r_prob = _retention.predict_proba(
                [[row.get("Age", 0), row.get("MonthlyIncome", 0), row.get("YearsAtCompany", 0)]]
            )[0]
            retention = "High Risk" if r_prob >= 0.5 else "Stable"

            # Promotion
            p_pred = _promotion.predict([[row.get("Age", 0), row.get("Department", ""), row.get("Education", ""), row.get("YearsAtCompany", 0)]])[0]
            promotion = "Eligible" if p_pred == 1 else "Not Eligible"

            # Sentiment
            feedback = row.get("Feedback", "")
            sentiment = "Neutral"
            if feedback:
                pol = TextBlob(feedback).sentiment.polarity
                sentiment = "Positive" if pol > 0.1 else ("Negative" if pol < -0.1 else "Neutral")

            predictions.append({
                "employee": row.get("EmployeeName", "Unknown"),
                "retention": retention,
                "promotion": promotion,
                "sentiment": sentiment,
            })

        return render(request, "hr_app/prediction.html", {"predictions": predictions})

    return render(request, "hr_app/csv_upload.html")


# load promotion model once
PROMOTION_MODEL = None
def load_promotion_model():
    global PROMOTION_MODEL
    if PROMOTION_MODEL is None:
        model_path = Path(__file__).resolve().parent / "ml" / "models" / "promotion.pkl"
        PROMOTION_MODEL = joblib.load(model_path)
    return PROMOTION_MODEL


@login_required
def predict_promotion(request):
    result, prob = None, None

    if request.method == "POST":
        try:
            data = {
                "city": request.POST.get("city") or "",
                "gender": request.POST.get("gender") or "",
                "relevent_experience": request.POST.get("experience_type") or "",
                "experience": int(request.POST.get("experience") or 0),
                "company_size": request.POST.get("company_size") or "",
                "company_type": request.POST.get("company_type") or "",
                "training_hours": int(request.POST.get("training_hours") or 0),

                    # 🔹 Missing fields
                "last_new_job": request.POST.get("last_new_job") or "",
                "enrolled_university": request.POST.get("enrolled_university") or "",
                "education_level": request.POST.get("education_level") or "",
                "city_development_index": float(request.POST.get("city_development_index") or 0),
                "major_discipline": request.POST.get("major_discipline") or "",
            }
            result, prob = promotion_predict(data)
        except Exception as e:
            result = f"Error: {str(e)}"

    return render(request, "hr_app/predict_promotion.html", {
        "result": result,
        "prob": prob
    })





# ——————————————————————————————————————
# Auth Views
# ——————————————————————————————————————
def register_view(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome.")
            return redirect("role_redirect")
    else:
        form = UserRegisterForm()
    return render(request, "hr_app/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("role_redirect")
    else:
        form = UserLoginForm()
    return render(request, "hr_app/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")

#hr


def hr_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "profile") or not request.user.profile.is_hr:
            messages.error(request, "❌ Access denied: HR only.")
            return redirect("role_redirect")
        return view_func(request, *args, **kwargs)
    return wrapper
# ——————————————————————————————————————
# Dashboard (KPIs + Charts)
# ——————————————————————————————————————


@login_required
def dashboard(request):
    total_employees = Employee.objects.count()
    retention_risks = Prediction.objects.filter(kind="retention", result="1").count()
    promotions = Prediction.objects.filter(kind="promotion", result="1").count()

    # Department distribution
    dept_distribution = Employee.objects.values("department").annotate(count=Count("id"))
    dept_labels = [d["department"] for d in dept_distribution]
    dept_counts = [d["count"] for d in dept_distribution]

    # Leave stats
    leave_stats = LeaveRequest.objects.values("status").annotate(count=Count("id"))
    leave_labels = [l["status"] for l in leave_stats]
    leave_counts = [l["count"] for l in leave_stats]

    # Sentiment stats
    feedbacks = Feedback.objects.all()
    sentiment_labels = ["Positive", "Neutral", "Negative"]
    sentiment_counts = [
        feedbacks.filter(sentiment="Positive").count(),
        feedbacks.filter(sentiment="Neutral").count(),
        feedbacks.filter(sentiment="Negative").count(),
    ]
    # Group feedback messages by sentiment
    sentiment_messages = {
        "Positive": list(feedbacks.filter(sentiment="Positive").values_list("text", flat=True)),
        "Neutral": list(feedbacks.filter(sentiment="Neutral").values_list("text", flat=True)),
        "Negative": list(feedbacks.filter(sentiment="Negative").values_list("text", flat=True)),
    }

    return render(request, "hr_app/dashboard.html", {
        "total_employees": total_employees,
        "retention_risks": retention_risks,
        "promotions": promotions,
        "dept_labels": dept_labels,
        "dept_counts": dept_counts,
        "leave_labels": leave_labels,
        "leave_counts": leave_counts,
        "sentiment_labels": sentiment_labels,
        "sentiment_counts": sentiment_counts,
        "sentiment_messages": sentiment_messages,
    })

@login_required
@hr_required
def hr_dashboard(request):
    total_employees = Employee.objects.count()
    retention_risks = Prediction.objects.filter(kind="retention", result="1").count()
    promotions = Prediction.objects.filter(kind="promotion", result="1").count()

    dept_distribution = Employee.objects.values("department").annotate(count=Count("id"))
    dept_labels = [d["department"] for d in dept_distribution]
    dept_counts = [d["count"] for d in dept_distribution]

    leave_stats = LeaveRequest.objects.values("status").annotate(count=Count("id"))
    leave_labels = [l["status"] for l in leave_stats]
    leave_counts = [l["count"] for l in leave_stats]

    feedbacks = Feedback.objects.all()
    sentiment_labels = ["Positive", "Neutral", "Negative"]
    sentiment_counts = [
        feedbacks.filter(sentiment="Positive").count(),
        feedbacks.filter(sentiment="Neutral").count(),
        feedbacks.filter(sentiment="Negative").count(),
    ]

    return render(request, "hr_app/hr_dashboard.html", {
        "total_employees": total_employees,
        "retention_risks": retention_risks,
        "promotions": promotions,
        "dept_labels": dept_labels,
        "dept_counts": dept_counts,
        "leave_labels": leave_labels,
        "leave_counts": leave_counts,
        "sentiment_labels": sentiment_labels,
        "sentiment_counts": sentiment_counts,
    })




# ——————————————————————————
# Employees
# ——————————————————————————
@login_required
def export_employees_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="employees.csv"'

    writer = csv.writer(response)
    writer.writerow(["Emp ID", "Name", "Department", "Age", "Salary", "Years at Company", "Job Title", "Location"])

    for e in Employee.objects.all():
        writer.writerow([e.emp_id, e.name, e.department, e.age, e.salary, e.years_at_company, e.job_title, e.location])

    return response

@login_required
def employee_dashboard(request):
    employee = getattr(request.user, "employee", None)
    my_leaves = LeaveRequest.objects.filter(employee=employee) if employee else []
    my_feedbacks = Feedback.objects.filter(employee=employee) if employee else []

    # If you want to show last predictions (optional)
    my_retention = Prediction.objects.filter(employee=employee, kind="retention").first() if employee else None
    my_promotion = Prediction.objects.filter(employee=employee, kind="promotion").first() if employee else None

    return render(request, "hr_app/employee_dashboard.html", {
        "employee": employee,
        "leaves": my_leaves,
        "feedbacks": my_feedbacks,
        "my_retention": my_retention,
        "my_promotion": my_promotion,
    })

# ——————————————————————————————————————
# Employee Directory & Search
# ——————————————————————————————————————
@login_required
def employee_directory(request):
    query = request.GET.get("q")
    if query:
        employees = Employee.objects.filter(name__icontains=query)
    else:
        employees = Employee.objects.all()
    
    # ✅ Pagination
    paginator = Paginator(employees, 10)  # 10 employees per page
    page_number = request.GET.get("page")
    employees_page = paginator.get_page(page_number)
    
    return render(request, "hr_app/employee_directory.html", {"employees": employees_page})


@login_required
def employee_add(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee added successfully ✅")
            return redirect("employee_directory")
    else:
        form = EmployeeForm()
    return render(request, "hr_app/employee_form.html", {"form": form})



@login_required
@hr_required
def employee_add_hr(request):
    if request.method == "POST":
        form = EmployeeCreateForm(request.POST)
        if form.is_valid():
            emp = form.save()
            messages.success(request, f"Employee created. Credentials issued to '{emp.user.username}'.")
            return redirect("employee_directory")
    else:
        form = EmployeeCreateForm()
    return render(request, "hr_app/employee_form_hr.html", {"form": form, "create": True})


@login_required
@hr_required
def employee_edit_hr(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)
    if request.method == "POST":
        form = EmployeeUpdateForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee updated.")
            return redirect("employee_directory")
    else:
        # Pre-fill role for convenience
        initial = {}
        if employee.user and hasattr(employee.user, "profile"):
            initial["role"] = employee.user.profile.role
        form = EmployeeUpdateForm(instance=employee, initial=initial)
    return render(request, "hr_app/employee_form_hr.html", {"form": form, "employee": employee})


@login_required
@hr_required
def employee_delete_hr(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)
    if request.method == "POST":
        # delete linked user too (optional)
        u = employee.user
        employee.delete()
        if u:
            u.delete()
        messages.success(request, "Employee and login removed.")
        return redirect("employee_directory")
    return render(request, "hr_app/employee_confirm_delete.html", {"employee": employee})


@login_required
def employee_edit(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Employee updated successfully ✅")
            return redirect("employee_directory")
    else:
        form = EmployeeForm(instance=employee)
    return render(request, "hr_app/employee_form.html", {"form": form, "edit": True})


@login_required
def employee_delete(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)
    if request.method == "POST":
        employee.delete()
        messages.success(request, "Employee deleted successfully 🗑️")
        return redirect("employee_directory")
    return render(request, "hr_app/employee_confirm_delete.html", {"employee": employee})

# ——————————————————————————————————————
# Feedback + Sentiment
# ——————————————————————————————————————
from textblob import TextBlob

@login_required
def feedback_submit(request, emp_id):
    employee = get_object_or_404(Employee, pk=emp_id)
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.employee = employee
            # Sentiment analysis
            sentiment_score = TextBlob(feedback.text).sentiment.polarity
            if sentiment_score > 0.1:
                feedback.sentiment = "Positive"
            elif sentiment_score < -0.1:
                feedback.sentiment = "Negative"
            else:
                feedback.sentiment = "Neutral"
            feedback.save()
            messages.success(request, "Feedback submitted!")
            return redirect("employee_directory")
    else:
        form = FeedbackForm()
    return render(request, "hr_app/feedback_form.html", {"form": form, "employee": employee})


@login_required
def feedback_history(request, emp_id):
    employee = get_object_or_404(Employee, pk=emp_id)
    feedbacks = employee.feedbacks.all()
    return render(request, "hr_app/feedback_history.html", {"employee": employee, "feedbacks": feedbacks})


# ——————————————————————————————————————
# CSV Upload + Predictions
# ——————————————————————————————————————
@login_required
def csv_upload(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]

            if not csv_file.name.endswith(".csv"):
                messages.error(request, "Please upload a valid CSV file.")
                return redirect("csv_upload")

            df = pd.read_csv(csv_file)

            for _, row in df.iterrows():
                Employee.objects.update_or_create(
                    emp_id=row.get("EmployeeNumber"),
                    defaults={
                        "name": row.get("EmployeeName", f"Emp {row.get('EmployeeNumber')}"),
                        "department": row.get("Department", "Unknown"),
                        "age": row.get("Age", 0),
                        "salary": row.get("MonthlyIncome", 0),
                        "years_at_company": row.get("YearsAtCompany", 0),
                    },
                )

            messages.success(request, "CSV uploaded successfully!")
            return redirect("employee_directory")
    else:
        form = CSVUploadForm()

    return render(request, "hr_app/csv_upload.html", {"form": form})


# ——————————————————————————————————————
# Messaging
# ——————————————————————————————————————
@login_required
def inbox(request):
    msgs = request.user.received_messages.all()
    return render(request, "hr_app/inbox.html", {"messages": msgs})


@login_required
def send_message(request):
    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.save()
            messages.success(request, "Message sent")
            return redirect("inbox")
    else:
        form = MessageForm()
    return render(request, "hr_app/message_form.html", {"form": form})

# ——————————————————————————
# Messages
# ——————————————————————————
@login_required
def export_messages_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="messages.csv"'

    writer = csv.writer(response)
    writer.writerow(["Sender", "Receiver", "Subject", "Body", "Is Read", "Created At"])

    for m in Message.objects.all():
        writer.writerow([m.sender.username, m.receiver.username, m.subject, m.body, m.is_read, m.created_at])

    return response


# ——————————————————————————————————————
# Leave Management
# ——————————————————————————————————————
@login_required
def leave_apply(request):
    employee = getattr(request.user, "employee", None)
    if not employee:
        messages.error(request, "Your account is not linked to an employee record. Please contact HR.")
        return redirect("employee_dashboard")

    if request.method == "POST":
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = employee
            leave.save()
            messages.success(request, "Leave request submitted.")
            return redirect("employee_dashboard")
    else:
        form = LeaveRequestForm()
    return render(request, "hr_app/leave_form.html", {"form": form})


@login_required
def leave_manage(request):
    if not request.user.profile.is_hr:
        messages.error(request, "Only HR can manage leave requests")
        return redirect("role_reedirect")

    if request.method == "POST":
        leave_id = request.POST.get("leave_id")
        action = request.POST.get("action")
        hr_comment = request.POST.get("hr_comment", "")

        try:
            leave = LeaveRequest.objects.get(id=leave_id)
            if leave.status == "Pending":  # only update pending ones
                leave.status = action
                leave.hr_comment = hr_comment
                leave.save()
                messages.success(request, f"Leave request {action.lower()} successfully.")
            else:
                messages.warning(request, "This request has already been processed.")
        except LeaveRequest.DoesNotExist:
            messages.error(request, "Leave request not found.")

        return redirect("leave_manage")  # reload page after action

    requests = LeaveRequest.objects.all()
    return render(request, "hr_app/leave_manage.html", {"requests": requests})

# ——————————————————————————
# Feedback
# ——————————————————————————
@login_required
def export_feedback_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="feedback.csv"'

    writer = csv.writer(response)
    writer.writerow(["Employee", "Feedback Text", "Sentiment", "Created At"])

    for f in Feedback.objects.all():
        writer.writerow([f.employee.name, f.text, f.sentiment, f.created_at])

    return response


BASE = Path(__file__).resolve().parent
_retention = None   # cache the model in memory

def retention_predict(feature_map: dict):
    global _retention
    if _retention is None:
        _retention = joblib.load(BASE / "ml" / "models" / "retention.pkl")

    df = pd.DataFrame([{
        "Age": feature_map.get("Age", 0),
        "MonthlyIncome": feature_map.get("MonthlyIncome", 0),
        "YearsAtCompany": feature_map.get("YearsAtCompany", 0),
        "JobRole": feature_map.get("JobRole", ""),
        "Department": feature_map.get("Department", ""),
        "EducationField": feature_map.get("EducationField", ""),
        "MaritalStatus": feature_map.get("MaritalStatus", ""),
    }])

    proba = _retention.predict_proba(df)[0][1]
    return int(proba >= 0.5), float(proba)



@login_required
def predict_retention_single(request):
    result, prob = None, None

    if request.method == "POST":
        data = {
            "Age": int(request.POST.get("age")),
            "MonthlyIncome": float(request.POST.get("monthly_income")),
            "YearsAtCompany": int(request.POST.get("years_at_company")),
            "Department": request.POST.get("department"),
        }
        yhat, p = retention_predict(data)
        result = "🚨 At Risk of Leaving" if yhat == 1 else "✅ Likely to Stay"
        prob = round(p * 100, 2)

    return render(request, "hr_app/predict_retention.html", {
        "prediction": result,  # matches template
        "prob": prob
    })

