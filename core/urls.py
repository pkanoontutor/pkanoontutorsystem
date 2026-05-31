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

    # Sheet Inventory
    path("sheet-inventory/", views.sheet_inventory_dashboard, name="sheet_inventory_dashboard"),
    path("sheet-inventory/scan/", views.sheet_inventory_scan, name="sheet_inventory_scan"),
    path("sheet-inventory/bulk-upload/", views.sheet_inventory_bulk_upload, name="sheet_inventory_bulk_upload"),
    path("sheet-inventory/export/", views.sheet_inventory_export, name="sheet_inventory_export"),
    path("sheet-inventory/sheet/<int:pk>/", views.sheet_inventory_profile, name="sheet_inventory_profile"),

    # Sheet print orders
    path("sheet-print-orders/", views.sheet_print_order_admin, name="sheet_print_order_admin"),
    path("print-shop/", views.print_shop_order_list, name="print_shop_order_list"),
    path("print-shop/order/<int:pk>/ready/", views.print_shop_mark_ready, name="print_shop_mark_ready"),




    # Course renewal notices
    path("course-renewal-notices/", views.course_renewal_notice_list, name="course_renewal_notice_list"),
    path("course-renewal-notices/create/<int:enrollment_id>/", views.course_renewal_notice_create, name="course_renewal_notice_create"),
    path("course-renewal-notices/create-installment/<int:enrollment_id>/", views.course_installment_notice_create, name="course_installment_notice_create"),
    path("course-renewal-notices/<int:pk>/", views.course_renewal_notice_detail, name="course_renewal_notice_detail"),
    path("course-renewal-notices/<int:pk>/mark-sent/", views.course_renewal_notice_mark_sent, name="course_renewal_notice_mark_sent"),
    path("course-renewal-notices/<int:pk>/unmark-sent/", views.course_renewal_notice_unmark_sent, name="course_renewal_notice_unmark_sent"),

    # Course payments / receipts
    path("course-payments/", views.course_payment_list, name="course_payment_list"),
    path("course-payments/new/", views.course_payment_create, name="course_payment_create"),
    path("course-payments/<int:pk>/", views.course_payment_detail, name="course_payment_detail"),
    path("course-payments/<int:pk>/receipt-image/", views.course_payment_receipt_image, name="course_payment_receipt_image"),
    path("course-payments/<int:pk>/cancel/", views.course_payment_cancel, name="course_payment_cancel"),


    # Tutor teaching update
    path("teaching/templates/", views.teaching_template_manage, name="teaching_template_manage"),
    path("teaching/weekly-setup/", views.teaching_weekly_setup, name="teaching_weekly_setup"),
    path("teaching/report/", views.teaching_update_report, name="teaching_update_report"),
    path("tutor-teaching-update/", views.tutor_teaching_update, name="tutor_teaching_update"),


    # Test score announcement
    path("test-scores/", views.test_score_round_list, name="test_score_round_list"),
    path("test-scores/round/<int:round_id>/login/", views.test_score_login, name="test_score_login"),
    path("test-scores/round/<int:round_id>/participant-search/", views.test_score_participant_search, name="test_score_participant_search"),
    path("test-scores/round/<int:round_id>/result/", views.test_score_result, name="test_score_result"),
    path("test-scores/round/<int:round_id>/logout/", views.test_score_logout, name="test_score_logout"),
    path("test-score-admin/", views.test_score_admin, name="test_score_admin"),
    path("test-score-admin/round/<int:round_id>/", views.test_score_round_manage, name="test_score_round_manage"),
    path("test-score-admin/round/<int:round_id>/summary/", views.test_score_round_summary, name="test_score_round_summary"),
    path("test-score-admin/round/<int:round_id>/template/", views.test_score_import_template, name="test_score_import_template"),
    path("test-score-admin/student-search/", views.test_score_student_search, name="test_score_student_search"),
    path("test-score-admin/admission-search/", views.test_score_admission_search, name="test_score_admission_search"),

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
