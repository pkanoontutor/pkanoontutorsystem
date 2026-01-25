from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # ✅ หน้าแรกของ core ให้เป็น Home (Public) เช่นกัน
    path("", views.home, name="home_page"),

    # Redirect ไป dashboard
    path("go-dashboard/", views.home_redirect, name="home_redirect"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Sheet Update
    path("sheet-update/", views.sheet_update, name="sheet_update"),

    # ✅ API: Sheet search (สำหรับ dropdown + search)
    path("api/sheets/search/", views.sheet_search_api, name="sheet_search_api"),

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

    # Student ID List (Public)
    path("student-id-list/", views.student_id_list, name="student_id_list"),

    # Sheet Inventory
    path("sheet-inventory/", views.sheet_inventory, name="sheet_inventory"),

    # Generate course notice
    path("generate/course-notice/", views.generate_course_notice, name="generate_course_notice"),

    # Export
    path("export/excel/", views.export_excel, name="export_excel"),
]
