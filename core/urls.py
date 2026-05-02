from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # หน้าแรก
    path("", views.home, name="home_page"),
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

    # Student ID List (Public)
    path("student-id-list/", views.student_id_list, name="student_id_list"),

    # Admin dashboard
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Generate course notice
    path("generate/course-notice/", views.generate_course_notice, name="generate_course_notice"),

    # Export
    path("export/excel/", views.export_excel, name="export_excel"),

    # =====================
    # QUIZ — Public (ไม่ต้อง login)
    # =====================
    path("quiz/", views.quiz_grade_select, name="quiz_grade_select"),
    path("quiz/register/", views.quiz_register, name="quiz_register"),
    path("quiz/take/<int:quiz_id>/", views.quiz_take, name="quiz_take"),
    path("quiz/submit/<int:attempt_id>/", views.quiz_submit, name="quiz_submit"),
    path("quiz/result/<str:session_key>/", views.quiz_result, name="quiz_result"),
    path("quiz/send-pdf/<str:session_key>/", views.quiz_send_pdf, name="quiz_send_pdf"),

    # =====================
    # QUIZ ADMIN — ต้อง login Django
    # =====================
    path("quiz-admin/", views.quiz_admin_list, name="quiz_admin_list"),
    path("quiz-admin/create/", views.quiz_admin_create, name="quiz_admin_create"),
    path("quiz-admin/<int:quiz_id>/edit/", views.quiz_admin_edit, name="quiz_admin_edit"),
    path("quiz-admin/<int:quiz_id>/toggle/", views.quiz_admin_toggle, name="quiz_admin_toggle"),
    path("quiz-admin/<int:quiz_id>/delete/", views.quiz_admin_delete, name="quiz_admin_delete"),
    path("quiz-admin/<int:quiz_id>/question/add/", views.quiz_question_add, name="quiz_question_add"),
    path("quiz-admin/question/<int:question_id>/edit/", views.quiz_question_edit, name="quiz_question_edit"),
    path("quiz-admin/question/<int:question_id>/delete/", views.quiz_question_delete, name="quiz_question_delete"),

    # =====================
    # QUIZ REPORT — ต้อง login Django
    # =====================
    path("quiz-report/", views.quiz_report, name="quiz_report"),
    path("quiz-report/export/", views.quiz_report_export, name="quiz_report_export"),
]
