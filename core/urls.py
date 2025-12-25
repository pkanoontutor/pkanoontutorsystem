from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home_redirect, name="home"),

    # หน้าเดียว: ซ้ายเช็คชื่อ / ขวาชีท
    path("dashboard/", views.dashboard, name="dashboard"),

    # ✅ เพิ่ม: Sheet Update (ตารางกรอกชีท)
    path("sheet-update/", views.sheet_update, name="sheet_update"),

    # submit เช็คชื่อแยกห้อง
    path("attendance/submit/", views.attendance_submit, name="attendance_submit"),

    # ใกล้ครบคอร์ส
    path("alerts/", views.alerts_dashboard, name="alerts_dashboard"),
    path("alerts/mark/", views.alerts_mark, name="alerts_mark"),

    # หน้าชีทแยก (optional)
    path("sheets/", views.sheet_dashboard, name="sheet_dashboard"),

    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("attendance-details/", views.attendance_details, name="attendance_details"),

    # ✅ Student Portal (ผู้ปกครอง)
    path("student-portal/", views.student_portal_login, name="student_portal_login"),
    path("student-portal/home/", views.student_portal_home, name="student_portal_home"),
    path("student-portal/logout/", views.student_portal_logout, name="student_portal_logout"),

    # ✅ Sheet Inventory (นับชีทคงเหลือ)
    path("sheet-inventory/", views.sheet_inventory, name="sheet_inventory"),

]
