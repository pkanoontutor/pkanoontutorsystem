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
    path("super-dashboard/", views.super_dashboard, name="super_dashboard"),
    path("pkanoon-admin-tool/", views.pkanoon_admin_tool, name="pkanoon_admin_tool"),
    path("pkanoon-admin-tool/cards/save/", views.admin_tool_card_save, name="admin_tool_card_save"),
    path("pkanoon-admin-tool/cards/delete/", views.admin_tool_card_delete, name="admin_tool_card_delete"),
    path("pkanoon-admin-tool/cards/reorder/", views.admin_tool_card_reorder, name="admin_tool_card_reorder"),
    path("pkanoon-admin-tool/cards/reset/", views.admin_tool_card_reset, name="admin_tool_card_reset"),
    path("pkanoon-admin-tool/low-stock-sheets/dismiss/", views.admin_tool_dismiss_low_stock_sheet, name="admin_tool_dismiss_low_stock_sheet"),
    path("pkanoon-admin-tool/admissions/action/", views.admin_tool_admission_action, name="admin_tool_admission_action"),
    path("pkanoon-admin-tool/low-stock-sheets/update-link/", views.admin_tool_update_sheet_link, name="admin_tool_update_sheet_link"),
    path("pkanoon-admin-tool/low-stock-sheets/print/", views.admin_tool_create_print_order, name="admin_tool_create_print_order"),
    path("learning-record/", views.learning_record, name="learning_record"),

    # Attendance
    path("attendance/submit/", views.attendance_submit, name="attendance_submit"),
    path("enrollment/mark-not-renewing/", views.enrollment_mark_not_renewing, name="enrollment_mark_not_renewing"),
    path("attendance-details/", views.attendance_details, name="attendance_details"),
    path("remaining-attendance/", views.remaining_attendance_search, name="remaining_attendance_search"),

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
    path("revenue-analysis/", views.revenue_analysis, name="revenue_analysis"),
    path("revenue-analysis/weekly-data/", views.revenue_analysis_weekly_data, name="revenue_analysis_weekly_data"),
    path("school-finance/export/", views.school_finance_export, name="school_finance_export"),
    path("school-finance/delete-expense/<int:pk>/", views.school_expense_delete, name="school_expense_delete"),
    path("school-finance/delete-payroll/<int:pk>/", views.tutor_payroll_delete, name="tutor_payroll_delete"),

    # Sheet Inventory

    # Weekly small test
    path("weekly-tests/", views.weekly_test_admin, name="weekly_test_admin"),
    path("weekly-tests/export/", views.weekly_test_export, name="weekly_test_export"),

    path("sheet-inventory/", views.sheet_inventory_dashboard, name="sheet_inventory_dashboard"),
    path("sheet-inventory/count/", views.sheet_inventory_count, name="sheet_inventory_count"),
    path("sheet-inventory/movements/", views.sheet_inventory_movements, name="sheet_inventory_movements"),
    path("sheet-inventory/scan/", views.sheet_inventory_scan, name="sheet_inventory_scan"),
    path("sheet-inventory/bulk-upload/", views.sheet_inventory_bulk_upload, name="sheet_inventory_bulk_upload"),
    path("sheet-inventory/export/", views.sheet_inventory_export, name="sheet_inventory_export"),
    path("sheet-inventory/sheet/<int:pk>/", views.sheet_inventory_profile, name="sheet_inventory_profile"),
    path("sheet-inventory/sheet/<int:pk>/cover/", views.sheet_inventory_cover_upload, name="sheet_inventory_cover_upload"),
    path("sheet-inventory/sheet/<int:pk>/documents/upload/", views.sheet_document_upload, name="sheet_document_upload"),
    path("sheet-inventory/documents/<int:pk>/delete/", views.sheet_document_delete, name="sheet_document_delete"),

    # Book library (คลังหนังสือ)
    path("books/", views.book_list, name="book_list"),
    path("sheet-allocation/", views.sheet_allocation_scan, name="sheet_allocation_scan"),
    path("sheet-allocation/save/", views.sheet_allocation_save, name="sheet_allocation_save"),
    path("sheet-allocation/report/", views.sheet_allocation_report, name="sheet_allocation_report"),

    # Sheet print orders
    path("sheet-print-orders/", views.sheet_print_order_admin, name="sheet_print_order_admin"),
    path("print-shop/", views.print_shop_order_list, name="print_shop_order_list"),
    path("print-shop/queue-preview/", views.print_shop_queue_preview, name="print_shop_queue_preview"),
    path("print-shop/order/<int:pk>/ready/", views.print_shop_mark_ready, name="print_shop_mark_ready"),
    path("print-shop/order/<int:pk>/update/", views.print_shop_update_order, name="print_shop_update_order"),




    # Course renewal notices
    path("course-renewal-notices/", views.course_renewal_notice_list, name="course_renewal_notice_list"),
    path("course-renewal-notices/create/<int:enrollment_id>/", views.course_renewal_notice_create, name="course_renewal_notice_create"),
    path("course-renewal-notices/create-installment/<int:enrollment_id>/", views.course_installment_notice_create, name="course_installment_notice_create"),
    path("course-renewal-notices/<int:pk>/", views.course_renewal_notice_detail, name="course_renewal_notice_detail"),
    path("course-renewal-notices/<int:pk>/mark-sent/", views.course_renewal_notice_mark_sent, name="course_renewal_notice_mark_sent"),
    path("course-renewal-notices/<int:pk>/unmark-sent/", views.course_renewal_notice_unmark_sent, name="course_renewal_notice_unmark_sent"),

    # Promotions
    path("promotions/", views.promotions_home, name="promotions_home"),
    path("promotions/friend-referral/", views.promotions_friend_referral, name="promotions_friend_referral"),

    # Course payments / receipts
    path("course-payments/", views.course_payment_list, name="course_payment_list"),
    path("course-payments/new/", views.course_payment_create, name="course_payment_create"),
    path("course-payments/quick-pick/<int:pk>/dismiss/", views.course_payment_dismiss_quick_pick, name="course_payment_dismiss_quick_pick"),
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
    path("online-course-p6/videos/", views.online_course_video_manage, name="online_course_video_manage"),

    # ✅ Star Quiz system
    path("star-quiz/", views.star_quiz_login, name="star_quiz_login"),
    path("star-quiz/home/", views.star_quiz_home, name="star_quiz_home"),
    path("star-quiz/take/<int:quiz_id>/", views.star_quiz_take, name="star_quiz_take"),
    path("star-quiz/result/<int:attempt_id>/", views.star_quiz_result, name="star_quiz_result"),
    path("star-quiz/manage/", views.star_quiz_manage, name="star_quiz_manage"),
    path("star-quiz/manage/<int:quiz_id>/", views.star_quiz_edit, name="star_quiz_edit"),
    path("star-quiz/manage/scores/", views.star_quiz_scores, name="star_quiz_scores"),

    # Student ID List (Public)
    path("student-id-list/", views.student_id_list, name="student_id_list"),

    # Admin dashboard
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Teaching schedule image generator
    path("teaching-schedule/", views.teaching_schedule_list, name="teaching_schedule_list"),
    path("teaching-schedule/edit/", views.teaching_schedule_editor, name="teaching_schedule_editor"),
    path("teaching-schedule/image/<int:pk>/", views.teaching_schedule_image, name="teaching_schedule_image"),
    path("teaching-schedule/exam-dates/", views.teaching_schedule_exam_dates, name="teaching_schedule_exam_dates"),
    path("teaching-schedule/rooms/", views.teaching_schedule_rooms, name="teaching_schedule_rooms"),
    path("teaching-schedule/tutors/", views.teaching_schedule_tutor_profiles, name="teaching_schedule_tutor_profiles"),
    path("teaching-schedule/image/<int:pk>/send-payroll/", views.teaching_schedule_send_payroll, name="teaching_schedule_send_payroll"),

    # Generate course notice
    path("generate/course-notice/", views.generate_course_notice, name="generate_course_notice"),

    # Export
    path("export/excel/", views.export_excel, name="export_excel"),
    path("export/excel/full/", views.export_full_excel, name="export_full_excel"),
]
