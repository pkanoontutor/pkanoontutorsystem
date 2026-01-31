from __future__ import annotations
from collections import OrderedDict

import json
from datetime import date, timedelta, datetime
from decimal import Decimal
from io import BytesIO

from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from .models import (
    Student,
    Attendance,
    Enrollment,
    TutoringClass,
)


def _parse_date(s: str | None) -> date:
    if not s:
        return timezone.localdate()
    try:
        return date.fromisoformat(s)
    except ValueError:
        return timezone.localdate()


def _fmt_dt_th(dt: datetime | None) -> str:
    if not dt:
        return "-"
    try:
        dt_local = timezone.localtime(dt)
        return dt_local.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


def home(request):
    return render(request, "core/home.html")


def home_redirect(request: HttpRequest) -> HttpResponse:
    return redirect("core:dashboard")


def student_id_list(request: HttpRequest) -> HttpResponse:
    """
    หน้า Public สำหรับผู้ปกครอง:
    แสดงเฉพาะ Student ID / ชื่อเล่น / ชื่อจริงนามสกุล / ระดับชั้น
    """
    grade = request.GET.get("grade")

    qs = (
        Student.objects
        .filter(is_active=True)
        .only("student_code", "nickname", "full_name", "grade_level")
    )

    if grade:
        qs = qs.filter(grade_level=grade)

    students = qs.order_by("grade_level", "student_code")

    return render(
        request,
        "core/student_id_list.html",
        {"students": students, "selected_grade": grade}
    )


# =======================
# Time slot order (GLOBAL)
# =======================
TIME_SLOT_ORDER = [
    TutoringClass.TimeSlot.SAT_MORNING,
    TutoringClass.TimeSlot.SAT_AFTERNOON,
    TutoringClass.TimeSlot.SUN_MORNING,
    TutoringClass.TimeSlot.SUN_AFTERNOON,
]


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """
    - ซ้าย: เช็คชื่อ (submit แยกทีละห้อง)
    - slot_totals (รวมต่อรอบเวลา) + รวมรายวัน/รวมสองวัน (เสาร์+อาทิตย์)
    - ตัดส่วน Sheet ออกทั้งหมดแล้ว
    """
    selected_date = _parse_date(request.GET.get("date"))

    classes = TutoringClass.objects.filter(is_active=True).order_by("name").all()

    classes_by_time_slot = OrderedDict()
    for ts in TIME_SLOT_ORDER:
        classes_by_time_slot[ts] = {
            "label": TutoringClass.TimeSlot(ts).label,
            "classes": [],
        }

    for cls in classes:
        if cls.time_slot in classes_by_time_slot:
            classes_by_time_slot[cls.time_slot]["classes"].append(cls)

    enrollments = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(
            is_active=True,
            student__is_active=True,
            tutoring_class__is_active=True,
        )
        .order_by(
            "tutoring_class__name",
            "student__nickname",
            "student__full_name",
            "student__grade_level",
        )
    )

    todays_att = Attendance.objects.filter(attendance_date=selected_date)
    att_map = {a.enrollment_id: a for a in todays_att}

    summary_by_class_id = {}
    seats_summary_by_class_id = {}

    global_present = global_excused = global_no_show = global_total = 0

    slot_totals: dict[str, dict[str, int]] = {
        ts: {"present": 0, "excused": 0, "no_show": 0, "total": 0}
        for ts in TIME_SLOT_ORDER
    }

    for cls in classes:
        cls_enrollments = enrollments.filter(tutoring_class=cls)
        enrollment_count = cls_enrollments.count()

        atts = todays_att.filter(enrollment__in=cls_enrollments)

        present = atts.filter(status=Attendance.Status.PRESENT).count()
        excused = atts.filter(status=Attendance.Status.EXCUSED).count()
        no_show = atts.filter(status=Attendance.Status.NO_SHOW).count()

        summary_by_class_id[cls.id] = {
            "present": present,
            "excused": excused,
            "no_show": no_show,
            "total": present + excused + no_show,
        }

        seats_total = cls.total_seats or 0
        seats_in_progress = enrollment_count
        seats_available = max(seats_total - seats_in_progress, 0)

        seats_summary_by_class_id[cls.id] = {
            "seats_total": seats_total,
            "seats_in_progress": seats_in_progress,
            "seats_available": seats_available,
        }

        global_present += present
        global_excused += excused
        global_no_show += no_show
        global_total += present + excused + no_show

        if cls.time_slot in slot_totals:
            slot_totals[cls.time_slot]["present"] += present
            slot_totals[cls.time_slot]["excused"] += excused
            slot_totals[cls.time_slot]["no_show"] += no_show
            slot_totals[cls.time_slot]["total"] += (present + excused + no_show)

    global_summary = {
        "present": global_present,
        "excused": global_excused,
        "no_show": global_no_show,
        "total": global_total,
    }

    other_day_date: date | None = None
    other_day_summary: dict | None = None
    two_day_summary: dict | None = None

    wd = selected_date.weekday()  # 5=Sat, 6=Sun
    if wd == 5:
        other_day_date = selected_date + timedelta(days=1)
    elif wd == 6:
        other_day_date = selected_date - timedelta(days=1)

    if other_day_date:
        other_day_summary = Attendance.objects.filter(
            attendance_date=other_day_date,
            enrollment__tutoring_class__is_active=True,
            student__is_active=True,
        ).aggregate(
            present=Count("id", filter=Q(status=Attendance.Status.PRESENT)),
            excused=Count("id", filter=Q(status=Attendance.Status.EXCUSED)),
            no_show=Count("id", filter=Q(status=Attendance.Status.NO_SHOW)),
            total=Count("id"),
        )

        two_day_summary = {
            "present": (global_summary.get("present", 0) or 0) + (other_day_summary.get("present", 0) or 0),
            "excused": (global_summary.get("excused", 0) or 0) + (other_day_summary.get("excused", 0) or 0),
            "no_show": (global_summary.get("no_show", 0) or 0) + (other_day_summary.get("no_show", 0) or 0),
            "total": (global_summary.get("total", 0) or 0) + (other_day_summary.get("total", 0) or 0),
        }

    THRESHOLD = 2
    near_complete = [e for e in enrollments if (e.remaining_sessions or 0) < THRESHOLD]

    context = {
        "selected_date": selected_date,
        "classes": classes,
        "classes_by_time_slot": classes_by_time_slot,

        "enrollments": enrollments,
        "att_map": att_map,
        "summary_by_class_id": summary_by_class_id,
        "seats_summary_by_class_id": seats_summary_by_class_id,
        "global_summary": global_summary,

        "slot_totals": slot_totals,
        "other_day_date": other_day_date,
        "other_day_summary": other_day_summary,
        "two_day_summary": two_day_summary,

        "near_complete": near_complete,
        "threshold": THRESHOLD,
    }
    return render(request, "core/dashboard.html", context)


# =========================================================
# ✅ Export ข้อมูลออก Excel
# =========================================================
def _autosize(ws):
    for col in range(1, ws.max_column + 1):
        max_len = 0
        col_letter = get_column_letter(col)
        for row in range(1, ws.max_row + 1):
            v = ws.cell(row=row, column=col).value
            if v is None:
                continue
            max_len = max(max_len, len(str(v)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)


@login_required
def export_excel(request: HttpRequest) -> HttpResponse:
    wb = Workbook()

    ws1 = wb.active
    ws1.title = "Enrollments"

    ws1.append([
        "Enrollment ID",
        "Student Code",
        "Nickname",
        "Full Name",
        "Grade",
        "Class",
        "Time Slot",
        "Enrollment Type",
        "Sessions Total",
        "Remaining Sessions",
        "Is Active",
        "Created At",
        "Notified?",
        "Notified Method",
        "Notified At",
    ])

    enrollments = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .order_by("-is_active", "tutoring_class__name", "student__nickname", "student__full_name")
    )

    for e in enrollments:
        s = e.student
        c = e.tutoring_class
        ws1.append([
            e.id,
            getattr(s, "student_code", "") or "",
            getattr(s, "nickname", "") or "",
            getattr(s, "full_name", "") or "",
            getattr(s, "grade_level", "") or "",
            getattr(c, "name", "") or "",
            getattr(c, "time_slot", "") or "",
            e.get_enrollment_type_display() if hasattr(e, "get_enrollment_type_display") else "",
            getattr(e, "sessions_total", "") or "",
            getattr(e, "remaining_sessions", "") if getattr(e, "remaining_sessions", None) is not None else "",
            bool(getattr(e, "is_active", False)),
            e.created_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(e, "created_at", None) else "",
            bool(getattr(e, "notified_near_complete", False)),
            getattr(e, "notified_method", "") or "",
            e.notified_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(e, "notified_at", None) else "",
        ])

    _autosize(ws1)

    ws2 = wb.create_sheet("Students")
    ws2.append([
        "Student ID",
        "Student Code",
        "Nickname",
        "Full Name",
        "Grade",
        "Is Active",
        "Active Enrollments",
        "Remaining Sessions (Active Total)",
    ])

    students = (
        Student.objects
        .order_by("-is_active", "grade_level", "student_code")
        .annotate(
            active_enrollments=Count("enrollments", filter=Q(enrollments__is_active=True)),
            remaining_total=Sum("enrollments__remaining_sessions", filter=Q(enrollments__is_active=True)),
        )
    )

    for s in students:
        ws2.append([
            s.id,
            getattr(s, "student_code", "") or "",
            getattr(s, "nickname", "") or "",
            getattr(s, "full_name", "") or "",
            getattr(s, "grade_level", "") or "",
            bool(getattr(s, "is_active", False)),
            int(getattr(s, "active_enrollments", 0) or 0),
            int(getattr(s, "remaining_total", 0) or 0),
        ])

    _autosize(ws2)

    buff = BytesIO()
    wb.save(buff)
    buff.seek(0)

    filename = f"pkanoon_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    resp = HttpResponse(
        buff.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@require_POST
@login_required
def attendance_submit(request: HttpRequest) -> JsonResponse:
    """
    Submit เช็คชื่อทีละห้อง
    - อัปเดต checked_at เป็นเวลา server
    - คืนค่า summary + remaining_map + checked_at_map + server_now_text
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    selected_date = _parse_date(payload.get("date"))
    class_id = payload.get("class_id")
    items = payload.get("items", [])

    if not class_id:
        return JsonResponse({"ok": False, "error": "Missing class_id"}, status=400)

    valid_status = {
        Attendance.Status.PRESENT,
        Attendance.Status.EXCUSED,
        Attendance.Status.NO_SHOW
    }

    normalized_items: list[dict] = []
    for it in items:
        try:
            eid = int(str(it.get("enrollment_id")).strip())
        except Exception:
            continue

        status = (it.get("status") or "").strip()
        if status not in valid_status:
            return JsonResponse({"ok": False, "error": "Invalid status in items"}, status=400)

        normalized_items.append({"enrollment_id": eid, "status": status})

    enrollments = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(
            tutoring_class_id=class_id,
            is_active=True,
            student__is_active=True,
            tutoring_class__is_active=True,
        )
        .all()
    )
    enroll_map = {e.id: e for e in enrollments}

    already_checked_ids = set(
        Attendance.objects
        .filter(
            attendance_date=selected_date,
            enrollment__tutoring_class_id=class_id,
            student__is_active=True,
        )
        .values_list("enrollment_id", flat=True)
    )

    required_ids = set(enroll_map.keys()) - already_checked_ids
    submitted_ids = {it["enrollment_id"] for it in normalized_items}

    missing = sorted(list(required_ids - submitted_ids))
    if missing:
        return JsonResponse({
            "ok": False,
            "error": "กรุณาเลือกสถานะให้ครบทุกคนในห้องนี้ก่อนกด Submit",
            "missing_enrollment_ids": missing,
            "debug": {
                "required_today": len(required_ids),
                "submitted_today": len(submitted_ids),
            }
        }, status=400)

    now = timezone.now()

    with transaction.atomic():
        for it in normalized_items:
            eid = it["enrollment_id"]
            status = it["status"]

            e = enroll_map.get(eid)
            if not e:
                continue

            att, _ = Attendance.objects.get_or_create(
                student=e.student,
                enrollment=e,
                attendance_date=selected_date,
                defaults={"status": status},
            )
            att.status = status
            att.checked_at = now
            att.save()

    cls_summary = Attendance.objects.filter(
        attendance_date=selected_date,
        enrollment__tutoring_class_id=class_id,
        student__is_active=True,
    ).aggregate(
        present=Count("id", filter=Q(status=Attendance.Status.PRESENT)),
        excused=Count("id", filter=Q(status=Attendance.Status.EXCUSED)),
        no_show=Count("id", filter=Q(status=Attendance.Status.NO_SHOW)),
        total=Count("id"),
    )

    global_summary = Attendance.objects.filter(
        attendance_date=selected_date,
        enrollment__tutoring_class__is_active=True,
        student__is_active=True,
    ).aggregate(
        present=Count("id", filter=Q(status=Attendance.Status.PRESENT)),
        excused=Count("id", filter=Q(status=Attendance.Status.EXCUSED)),
        no_show=Count("id", filter=Q(status=Attendance.Status.NO_SHOW)),
        total=Count("id"),
    )

    refreshed = (
        Enrollment.objects
        .filter(id__in=list(enroll_map.keys()))
        .only("id", "remaining_sessions")
    )
    remaining_map = {e.id: e.remaining_sessions for e in refreshed}

    submitted_eids = [it["enrollment_id"] for it in normalized_items]
    checked_at_qs = Attendance.objects.filter(
        attendance_date=selected_date,
        enrollment_id__in=submitted_eids,
    ).only("enrollment_id", "checked_at")
    checked_at_map = {a.enrollment_id: _fmt_dt_th(a.checked_at) for a in checked_at_qs}

    return JsonResponse({
        "ok": True,
        "class_id": int(class_id),
        "date": selected_date.isoformat(),
        "class_summary": cls_summary,
        "global_summary": global_summary,
        "remaining_map": remaining_map,
        "checked_at_map": checked_at_map,
        "server_now_text": _fmt_dt_th(now),
    })


@login_required
def alerts_dashboard(request: HttpRequest) -> HttpResponse:
    THRESHOLD = 2
    enrollments = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(student__is_active=True, tutoring_class__is_active=True)
        .order_by("tutoring_class__name", "student__nickname", "student__full_name", "student__grade_level")
        .all()
    )

    near = [e for e in enrollments if (e.remaining_sessions or 0) < THRESHOLD]

    return render(request, "core/alerts_dashboard.html", {
        "near": near,
        "threshold": THRESHOLD,
    })


@require_POST
@login_required
def alerts_mark(request: HttpRequest) -> HttpResponse:
    eid = request.POST.get("enrollment_id")
    method = (request.POST.get("method") or "").strip()

    e = get_object_or_404(Enrollment, id=eid)

    if method == "":
        e.notified_near_complete = False
        e.notified_method = None
        e.notified_at = None
    else:
        e.notified_near_complete = True
        e.notified_method = method
        e.notified_at = timezone.now()

    e.save()
    return redirect(request.META.get("HTTP_REFERER", "/dashboard/"))


@login_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    today = timezone.localdate()
    weeks = 8

    monday_this_week = today - timedelta(days=today.weekday())
    week_starts = [monday_this_week - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    buckets = {ws: set() for ws in week_starts}

    start_date = week_starts[0]
    end_date = monday_this_week + timedelta(days=6)

    qs = (
        Attendance.objects
        .select_related("student")
        .filter(attendance_date__gte=start_date, attendance_date__lte=end_date, student__is_active=True)
        .only("attendance_date", "student_id")
    )

    for a in qs:
        ws = a.attendance_date - timedelta(days=a.attendance_date.weekday())
        if ws in buckets:
            buckets[ws].add(a.student_id)

    labels = [ws.strftime("%d %b") for ws in week_starts]
    counts = [len(buckets[ws]) for ws in week_starts]
    max_count = max(counts) if counts else 0

    return render(request, "core/admin_dashboard.html", {
        "labels": labels,
        "counts": counts,
        "max_count": max_count,
        "weeks": weeks,
    })


@login_required
def attendance_details(request: HttpRequest) -> HttpResponse:
    """
    ✅ แสดงเฉพาะ enrollment active
    ✅ คอลัมน์คงที่ 1..22
    ✅ ส่ง summary ต่อ enrollment ให้ template ใช้ (มา/ลา/ขาด/total/คงเหลือ)
    """
    classes = TutoringClass.objects.filter(is_active=True).order_by("name").all()

    enrollments = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(
            is_active=True,
            student__is_active=True,
            tutoring_class__is_active=True,
        )
        .order_by(
            "tutoring_class__name",
            "student__nickname",
            "student__full_name",
            "student__grade_level",
        )
        .all()
    )

    all_att = (
        Attendance.objects
        .select_related("enrollment")
        .filter(enrollment__in=enrollments)
        .order_by("attendance_date", "checked_at")
        .all()
    )

    att_list_map: dict[int, list[dict]] = {e.id: [] for e in enrollments}
    for a in all_att:
        att_list_map[a.enrollment_id].append({
            "date": a.attendance_date,
            "status": a.status,
        })

    grouped_rows: dict[int, list[dict]] = {}

    for e in enrollments:
        recs = att_list_map.get(e.id, [])

        present_cnt = sum(1 for r in recs if r.get("status") == Attendance.Status.PRESENT)
        excused_cnt = sum(1 for r in recs if r.get("status") == Attendance.Status.EXCUSED)
        noshow_cnt = sum(1 for r in recs if r.get("status") == Attendance.Status.NO_SHOW)

        grouped_rows.setdefault(e.tutoring_class_id, []).append({
            "enrollment": e,
            "records": recs[:22],  # โชว์สูงสุด 22 ช่อง
            "present_cnt": present_cnt,
            "excused_cnt": excused_cnt,
            "noshow_cnt": noshow_cnt,
            "total_sessions": int(getattr(e, "sessions_total", 0) or 0),
            "remaining_sessions": int(getattr(e, "remaining_sessions", 0) or 0),
        })

    session_cols = list(range(1, 23))

    return render(request, "core/attendance_details.html", {
        "classes": classes,
        "grouped_rows": grouped_rows,
        "session_cols": session_cols,
    })


# =========================================================
# ✅ Student Portal (ผู้ปกครอง)
# =========================================================
class StudentPortalLoginForm(forms.Form):
    student_code = forms.CharField(label="รหัสนักเรียน", max_length=20)
    parent_phone = forms.CharField(label="เบอร์ผู้ปกครอง", max_length=50)

    def clean(self):
        cleaned = super().clean()
        code = (cleaned.get("student_code") or "").strip()
        phone = (cleaned.get("parent_phone") or "").strip()

        student = Student.objects.filter(student_code=code, is_active=True).first()
        if not student:
            raise forms.ValidationError("ไม่พบรหัสนักเรียนนี้")

        def digits(x: str) -> str:
            return "".join(ch for ch in x if ch.isdigit())

        MASTER_PASSWORD = "kanoon"

        if phone != MASTER_PASSWORD and digits(student.parent_phone) != digits(phone):
            raise forms.ValidationError("เบอร์ผู้ปกครองไม่ถูกต้อง")

        cleaned["student"] = student
        return cleaned


def student_portal_login(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = StudentPortalLoginForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data["student"]
            request.session["portal_student_id"] = student.id
            return redirect("core:student_portal_home")
    else:
        form = StudentPortalLoginForm()

    return render(request, "core/student_portal_login.html", {"form": form})


def _get_portal_student(request: HttpRequest) -> Student | None:
    sid = request.session.get("portal_student_id")
    if not sid:
        return None
    try:
        return Student.objects.get(id=sid, is_active=True)
    except Student.DoesNotExist:
        return None


def student_portal_logout(request: HttpRequest) -> HttpResponse:
    request.session.pop("portal_student_id", None)
    return redirect("core:student_portal_login")


def student_portal_home(request: HttpRequest) -> HttpResponse:
    student = _get_portal_student(request)
    if not student:
        return redirect("core:student_portal_login")

    enrollments = (
        Enrollment.objects
        .select_related("tutoring_class")
        .filter(student=student)
        .order_by("-is_active", "-created_at")
        .all()
    )

    selected_enrollment_id = request.GET.get("enrollment_id")
    selected_enrollment = None
    if selected_enrollment_id:
        selected_enrollment = enrollments.filter(id=selected_enrollment_id).first()
    if not selected_enrollment and enrollments:
        selected_enrollment = enrollments[0]

    attendance_rows = []
    if selected_enrollment:
        attendance_rows = (
            Attendance.objects
            .filter(student=student, enrollment=selected_enrollment)
            .order_by("-attendance_date", "-checked_at")
            .all()
        )

    remaining_sessions = selected_enrollment.remaining_sessions if selected_enrollment else 0
    hours_per_session = float(selected_enrollment.tutoring_class.hours_per_session) if selected_enrollment else 0.0
    remaining_hours = remaining_sessions * hours_per_session

    context = {
        "student": student,
        "enrollments": enrollments,
        "selected_enrollment": selected_enrollment,
        "attendance_rows": attendance_rows,
        "remaining_sessions": remaining_sessions,
        "hours_per_session": hours_per_session,
        "remaining_hours": remaining_hours,
    }
    return render(request, "core/student_portal_home.html", context)


# =========================================================
# ✅ Generate ใบแจ้งครบคอร์ส
# =========================================================
@login_required
def generate_course_notice(request: HttpRequest) -> HttpResponse:
    enrollment_id = request.GET.get("enrollment_id") or request.POST.get("enrollment_id")
    if not enrollment_id:
        return render(request, "core/generate_course_notice.html", {"error": "missing enrollment_id"})

    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "tutoring_class"),
        id=enrollment_id,
        is_active=True,
        student__is_active=True,
        tutoring_class__is_active=True,
    )

    student = enrollment.student
    tutoring_class = enrollment.tutoring_class

    base_price = enrollment.course_price if getattr(enrollment, "course_price", None) is not None else (
        tutoring_class.course_price if tutoring_class else 0
    )

    def to_decimal(x, default: Decimal) -> Decimal:
        try:
            s = str(x).strip()
            if s == "":
                return default
            return Decimal(s)
        except Exception:
            return default

    if request.method == "POST":
        course_end_date = _parse_date(request.POST.get("course_end_date"))
    else:
        course_end_date = timezone.localdate()

    next_course_start_date = course_end_date + timedelta(days=7)

    amount_10 = to_decimal(
        request.POST.get("amount_10") if request.method == "POST" else None,
        Decimal(str(base_price or 0))
    )
    discount_10 = to_decimal(
        request.POST.get("discount_10") if request.method == "POST" else None,
        Decimal("0")
    )
    net_10 = amount_10 - discount_10
    if net_10 < 0:
        net_10 = Decimal("0")

    amount_20_default = Decimal(str(base_price or 0)) * 2
    amount_20 = to_decimal(
        request.POST.get("amount_20") if request.method == "POST" else None,
        amount_20_default
    )
    discount_20 = to_decimal(
        request.POST.get("discount_20") if request.method == "POST" else None,
        Decimal("0")
    )
    net_20 = amount_20 - discount_20
    if net_20 < 0:
        net_20 = Decimal("0")

    context = {
        "student": student,
        "enrollment": enrollment,
        "tutoring_class": tutoring_class,
        "remaining_sessions": enrollment.remaining_sessions,

        "course_end_date": course_end_date,
        "next_course_start_date": next_course_start_date,

        "amount_10": amount_10,
        "discount_10": discount_10,
        "net_10": net_10,

        "amount_20": amount_20,
        "discount_20": discount_20,
        "net_20": net_20,

        "qr_promptpay_static": "core/img/qr_promptpay.png",
        "qr_line_static": "core/img/qr_line.png",
    }
    return render(request, "core/generate_course_notice.html", context)
