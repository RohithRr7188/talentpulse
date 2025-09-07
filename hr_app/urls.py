from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Role redirect after login
    path("redirect/", views.role_redirect, name="role_redirect"),

     # Dashboards
    path("hr/dashboard/", views.hr_dashboard, name="hr_dashboard"),
    path("employee/dashboard/", views.employee_dashboard, name="employee_dashboard"),


    # Employee
    path("employees/", views.employee_directory, name="employee_directory"),
    path("employees/add/", views.employee_add_hr, name="employee_add_hr"),

    path("employee/<int:emp_id>/edit/", views.employee_edit_hr, name="employee_edit_hr"),
    path("employee/<int:emp_id>/delete/", views.employee_delete_hr, name="employee_delete_hr"),
    path("export/employees/", views.export_employees_csv, name="export_employees_csv"), 

    # Feedback
    path("feedback/<int:emp_id>/", views.feedback_submit, name="feedback_submit"),
    path("feedback/history/<int:emp_id>/", views.feedback_history, name="feedback_history"),

    # CSV Upload
    path("csv-upload/", views.csv_upload, name="csv_upload"),
    path("csv/predict/", views.csv_predict_upload, name="csv_predict_upload"),

     
    path("export/messages/", views.export_messages_csv, name="export_messages_csv"),
    path("export/feedback/", views.export_feedback_csv, name="export_feedback_csv"),

    # Messaging
    path("inbox/", views.inbox, name="inbox"),
    path("send-message/", views.send_message, name="send_message"),

    # Leave Management
    path("leave/apply/", views.leave_apply, name="leave_apply"),
    path("hr/leave/manage/", views.leave_manage, name="leave_manage"),
      


    # Predictions
    path("predict/retention/", views.predict_retention_single, name="predict_retention"),
    path("predict/promotion/", views.predict_promotion, name="predict_promotion"),

    # CSV directory import & bulk predict
    path("hr/csv/upload/", views.csv_upload, name="csv_upload"),
    path("hr/csv/predict/", views.csv_predict_upload, name="csv_predict_upload"),
]
