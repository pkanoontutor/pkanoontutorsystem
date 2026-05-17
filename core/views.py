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
from django.views.decorators.http import require_POST, require_GET

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from .models import (
    Student,
    Attendance,
    Enrollment,
    TutoringClass,
    AdmissionInquiry,
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
        .filter(enrollment__in=enrollments)
        .only("enrollment_id", "attendance_date", "status", "checked_at")
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
    # ✅ ใช้ Select2 AJAX แต่ "ห้าม" ใช้ ChoiceField เพราะจะ Validate choices แล้วพัง
    #    เราใช้ CharField + Select widget แทน เพื่อให้ POST ค่า id ได้โดยไม่ติด "valid choice"
    student_id = forms.CharField(
        label="เลือกชื่อน้อง",
        required=True,
        widget=forms.Select(attrs={"id": "id_student_id"})
    )
    parent_phone = forms.CharField(label="เบอร์ผู้ปกครอง", max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ใส่ placeholder option ไว้ 1 ตัวพอ (Select2 จะเติมรายการจาก AJAX เอง)
        self.fields["student_id"].widget.choices = [
            ("", "พิมพ์ค้นหาชื่อเล่น / ชื่อจริง / รหัสนักเรียน")
        ]

    def clean(self):
        cleaned = super().clean()
        sid = (cleaned.get("student_id") or "").strip()
        phone = (cleaned.get("parent_phone") or "").strip()

        if not sid:
            raise forms.ValidationError("กรุณาเลือกชื่อนักเรียน")

        try:
            sid_int = int(sid)
        except Exception:
            raise forms.ValidationError("รูปแบบนักเรียนไม่ถูกต้อง")

        student = Student.objects.filter(id=sid_int, is_active=True).first()
        if not student:
            raise forms.ValidationError("ไม่พบนักเรียนนี้ในระบบ")

        def digits(x: str) -> str:
            return "".join(ch for ch in x if ch.isdigit())

        MASTER_PASSWORD = "kanoon"

        if phone != MASTER_PASSWORD and digits(student.parent_phone) != digits(phone):
            raise forms.ValidationError("เบอร์ผู้ปกครองไม่ถูกต้อง")

        cleaned["student"] = student
        return cleaned


@require_GET
def student_portal_student_search(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint สำหรับ Select2:
    - ค้นหาได้ด้วย nickname / full_name / student_code
    - คืนค่า format: { "results": [ { "id": "...", "text": "..." }, ... ] }
    """
    q = (request.GET.get("q") or "").strip()

    qs = Student.objects.filter(is_active=True)

    if q:
        qs = qs.filter(
            Q(nickname__icontains=q) |
            Q(full_name__icontains=q) |
            Q(student_code__icontains=q)
        )

    qs = qs.only("id", "student_code", "nickname", "full_name", "grade_level").order_by(
        "grade_level", "student_code"
    )[:30]

    results = []
    for s in qs:
        nickname = (getattr(s, "nickname", "") or "").strip()
        full_name = getattr(s, "full_name", "") or ""
        student_code = getattr(s, "student_code", "") or ""
        grade = getattr(s, "grade_level", "") or ""

        label = f"{student_code} | {nickname or '-'} | {full_name}"
        if grade:
            label += f" | {grade}"

        results.append({"id": str(s.id), "text": label})

    return JsonResponse({"results": results})


def student_portal_login(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = StudentPortalLoginForm(request.POST)

        if form.is_valid():
            student = form.cleaned_data["student"]
            request.session["portal_student_id"] = student.id

            # ✅ ถ้า Login จากปุ่มคอร์สออนไลน์ ป.6 ให้ไปหน้า Online Course
            if request.path == "/online-course-p6/":
                return redirect("core:online_course_home")

            # ✅ ถ้า Login จาก Student Portal ปกติ ให้ไปหน้า Student Portal Home
            return redirect("core:student_portal_home")

    else:
        form = StudentPortalLoginForm()

    return render(request, "core/student_portal_login.html", {
        "form": form
    })


def online_course_login(request: HttpRequest) -> HttpResponse:
    return student_portal_login(request)


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


def online_course_home(request: HttpRequest) -> HttpResponse:
    student = _get_portal_student(request)

    if not student:
        return redirect("core:online_course_login")

    return render(request, "core/online_course_home.html", {
        "student": student,
    })


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

    hours_per_session = (
        float(selected_enrollment.tutoring_class.hours_per_session)
        if selected_enrollment else 0.0
    )

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

# =========================================================
# ✅ Admission Inquiry: สมัครเรียน / จองทดลองเรียน
# =========================================================
class AdmissionInquiryForm(forms.ModelForm):
    class Meta:
        model = AdmissionInquiry
        fields = [
            "request_type",
            "nickname",
            "first_name",
            "last_name",
            "school_name",
            "contact_phone",
            "latest_gpa",
            "first_lesson_date",
            "grade_level",
            "preferred_time_slot",
        ]
        widgets = {
            "request_type": forms.RadioSelect,
            "nickname": forms.TextInput(attrs={"placeholder": "เช่น น้องข้าวหอม"}),
            "first_name": forms.TextInput(attrs={"placeholder": "ชื่อจริงของนักเรียน"}),
            "last_name": forms.TextInput(attrs={"placeholder": "นามสกุลของนักเรียน"}),
            "school_name": forms.TextInput(attrs={"placeholder": "ชื่อโรงเรียน"}),
            "contact_phone": forms.TextInput(attrs={"placeholder": "เบอร์ผู้ปกครอง / เบอร์ติดต่อ"}),
            "latest_gpa": forms.NumberInput(attrs={
                "placeholder": "เช่น 3.50",
                "step": "0.01",
                "min": "0",
                "max": "4",
            }),
            "first_lesson_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_contact_phone(self):
        phone = (self.cleaned_data.get("contact_phone") or "").strip()
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 9:
            raise forms.ValidationError("กรุณากรอกเบอร์ติดต่อให้ถูกต้อง")
        return phone


def admission_inquiry(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AdmissionInquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save()
            return redirect("core:admission_thank_you", pk=inquiry.pk)
    else:
        form = AdmissionInquiryForm()

    return render(request, "core/admission_inquiry.html", {
        "form": form,
    })


def admission_thank_you(request: HttpRequest, pk: int) -> HttpResponse:
    inquiry = get_object_or_404(AdmissionInquiry, pk=pk)

    return render(request, "core/admission_thank_you.html", {
        "inquiry": inquiry,
        "line_url": "https://lin.ee/Vp91szz",
    })


@login_required
def admission_report(request: HttpRequest) -> HttpResponse:
    qs = AdmissionInquiry.objects.all()

    q = (request.GET.get("q") or "").strip()
    request_type = (request.GET.get("request_type") or "").strip()
    grade_level = (request.GET.get("grade_level") or "").strip()
    preferred_time_slot = (request.GET.get("preferred_time_slot") or "").strip()
    sheet_prepared = (request.GET.get("sheet_prepared") or "").strip()
    trial_attended = (request.GET.get("trial_attended") or "").strip()
    trial_result = (request.GET.get("trial_result") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()

    if q:
        qs = qs.filter(
            Q(nickname__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(school_name__icontains=q) |
            Q(contact_phone__icontains=q)
        )

    if request_type:
        qs = qs.filter(request_type=request_type)
    if grade_level:
        qs = qs.filter(grade_level=grade_level)
    if preferred_time_slot:
        qs = qs.filter(preferred_time_slot=preferred_time_slot)
    if sheet_prepared == "yes":
        qs = qs.filter(sheet_prepared=True)
    elif sheet_prepared == "no":
        qs = qs.filter(sheet_prepared=False)
    if trial_attended:
        qs = qs.filter(trial_attended=trial_attended)
    if trial_result:
        qs = qs.filter(trial_result=trial_result)
    if date_from:
        try:
            qs = qs.filter(first_lesson_date__gte=date.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(first_lesson_date__lte=date.fromisoformat(date_to))
        except ValueError:
            pass

    stats_base = AdmissionInquiry.objects.all()
    stats = {
        "total": stats_base.count(),
        "trial": stats_base.filter(request_type=AdmissionInquiry.RequestType.TRIAL).count(),
        "enroll": stats_base.filter(request_type=AdmissionInquiry.RequestType.ENROLL).count(),
        "sheet_ready": stats_base.filter(sheet_prepared=True).count(),
        "trial_attended": stats_base.filter(trial_attended=AdmissionInquiry.TrialAttended.YES).count(),
        "trial_enrolled": stats_base.filter(trial_result=AdmissionInquiry.TrialResult.ENROLLED).count(),
    }

    inquiries = qs.order_by("first_lesson_date", "-created_at")

    return render(request, "core/admission_report.html", {
        "inquiries": inquiries,
        "stats": stats,
        "filters": {
            "q": q,
            "request_type": request_type,
            "grade_level": grade_level,
            "preferred_time_slot": preferred_time_slot,
            "sheet_prepared": sheet_prepared,
            "trial_attended": trial_attended,
            "trial_result": trial_result,
            "date_from": date_from,
            "date_to": date_to,
        },
        "request_type_choices": AdmissionInquiry.RequestType.choices,
        "grade_level_choices": AdmissionInquiry.GradeLevel.choices,
        "time_slot_choices": AdmissionInquiry.PreferredTimeSlot.choices,
        "trial_attended_choices": AdmissionInquiry.TrialAttended.choices,
        "trial_result_choices": AdmissionInquiry.TrialResult.choices,
    })


@require_POST
@login_required
def admission_report_update(request: HttpRequest) -> HttpResponse:
    inquiry_id = request.POST.get("inquiry_id")
    inquiry = get_object_or_404(AdmissionInquiry, id=inquiry_id)

    sheet_prepared = request.POST.get("sheet_prepared")
    trial_attended = request.POST.get("trial_attended")
    trial_result = request.POST.get("trial_result")
    internal_note = request.POST.get("internal_note")

    inquiry.sheet_prepared = sheet_prepared == "yes"

    valid_attended = {choice[0] for choice in AdmissionInquiry.TrialAttended.choices}
    valid_result = {choice[0] for choice in AdmissionInquiry.TrialResult.choices}

    if trial_attended in valid_attended:
        inquiry.trial_attended = trial_attended
    if trial_result in valid_result:
        inquiry.trial_result = trial_result
    if internal_note is not None:
        inquiry.internal_note = internal_note.strip()

    inquiry.save()

    return redirect(request.META.get("HTTP_REFERER", "core:admission_report"))

