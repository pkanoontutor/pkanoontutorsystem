from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # ✅ หน้าแรกของ core ให้เป็น Home (Public)
    path("", views.home, name="home_page"),

    # Redirect ไป dashboard
    path("go-dashboard/", views.home_redirect, name="home_redirect"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Attendance
    path("attendance/submit/", views.attendance_submit, name="attendance_submit"),
    path("attendance-details/", views.attendance_details, name="attendance_details"),

    # Alerts
    path("alerts/", views.alerts_dashboard, name="alerts_dashboard"),
    path("alerts/mark/", views.alerts_mark, name="alerts_mark"),

    # Student Portal
    path("student-portal/", views.student_portal_login, name="student_portal_login"),
    path("student-portal/student-search/", views.student_portal_student_search, name="student_portal_student_search"),
    path("student-portal/home/", views.student_portal_home, name="student_portal_home"),
    path("student-portal/logout/", views.student_portal_logout, name="student_portal_logout"),

    # ✅ Online Course P6
    path("online-course-p6/", views.online_course_login, name="online_course_login"),
    path("online-course-p6/home/", views.online_course_home, name="online_course_home"),

    # Student ID List (Public)
    path("student-id-list/", views.student_id_list, name="student_id_list"),

    # Admin dashboard
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Generate course notice
    path("generate/course-notice/", views.generate_course_notice, name="generate_course_notice"),

    # Export
    path("export/excel/", views.export_excel, name="export_excel"),
]
