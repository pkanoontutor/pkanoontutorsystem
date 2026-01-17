from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home_redirect, name="home"),

    # หน้า Home
    path("home/", views.home, name="home_page"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Sheet Update
    path("sheet-update/", views.sheet_update, name="sheet_update"),

    # Attendance
    path("attendance/submit/", views.attendance_submit, name="attendance_submit"),

    # Alerts
    path("alerts/", views.alerts_dashboard, name="alerts_dashboard"),
    path("alerts/mark/", views.alerts_mark, name="alerts_mark"),

    # Sheet
    path("sheets/", views.sheet_dashboard, name="sheet_dashboard"),

    # Admin dashboard
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("attendance-details/", views.attendance_details, name="attendance_details"),

    # Student Portal
    path("student-portal/", views.student_portal_login, name="student_portal_login"),
    path("student-portal/home/", views.student_portal_home, name="student_portal_home"),
    path("student-portal/logout/", views.student_portal_logout, name="student_portal_logout"),

    # ✅ NEW: Student ID List (Public)
    path("student-id-list/", views.student_id_list, name="student_id_list"),

    # Sheet Inventory
    path("sheet-inventory/", views.sheet_inventory, name="sheet_inventory"),

    # ✅ NEW: Generate course notice (prefill by enrollment_id)
    path("generate/course-notice/", views.generate_course_notice, name="generate_course_notice"),
]
