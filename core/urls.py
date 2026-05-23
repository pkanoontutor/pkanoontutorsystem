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
    path("pkanoon-admin-tool/", views.pkanoon_admin_tool, name="pkanoon_admin_tool"),

    # Attendance
    path("attendance/submit/", views.attendance_submit, name="attendance_submit"),
    path("attendance-details/", views.attendance_details, name="attendance_details"),

    # Alerts
    path("alerts/", views.alerts_dashboard, name="alerts_dashboard"),
    path("alerts/mark/", views.alerts_mark, name="alerts_mark"),


    # Admission / Trial Booking
    path("admission/", views.admission_inquiry, name="admission_inquiry"),
    path("admission/thank-you/<int:pk>/", views.admission_thank_you, name="admission_thank_you"),
    path("admission-report/", views.admission_report, name="admission_report"),
    path("admission-report/update/", views.admission_report_update, name="admission_report_update"),


    # School overview / finance
    path("school-overview/", views.school_overview, name="school_overview"),
    path("school-finance/", views.school_finance, name="school_finance"),
    path("school-finance/export/", views.school_finance_export, name="school_finance_export"),
    path("school-finance/delete-expense/<int:pk>/", views.school_expense_delete, name="school_expense_delete"),
    path("school-finance/delete-payroll/<int:pk>/", views.tutor_payroll_delete, name="tutor_payroll_delete"),


    # Course payments / receipts
    path("course-payments/", views.course_payment_list, name="course_payment_list"),
    path("course-payments/new/", views.course_payment_create, name="course_payment_create"),
    path("course-payments/<int:pk>/", views.course_payment_detail, name="course_payment_detail"),
    path("course-payments/<int:pk>/receipt-image/", views.course_payment_receipt_image, name="course_payment_receipt_image"),
    path("course-payments/<int:pk>/cancel/", views.course_payment_cancel, name="course_payment_cancel"),

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
