from django.apps import AppConfig

class HrAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hr_app"

    def ready(self):
        # Import and call create_admin only once when server starts
        try:
            from .views import create_admin
            create_admin()
        except Exception as e:
            print("⚠️ Could not create admin:", e)
