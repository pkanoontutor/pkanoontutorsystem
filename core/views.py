from __future__ import annotations
from collections import OrderedDict

import io
import json
import secrets
from datetime import date, timedelta, datetime
from decimal import Decimal
from io import BytesIO

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from .models import (
    Student, Attendance, Enrollment, TutoringClass,
    Quiz, Question, Choice, QuizAttempt, QuizAnswer,
    GRADE_CHOICES, SUBJECT_DISPLAY_ORDER,
)


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

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
        return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


# ─────────────────────────────────────────
# Home
# ─────────────────────────────────────────

def home(request):
    return render(request, "core/home.html")


def home_redirect(request: HttpRequest) -> HttpResponse:
    return redirect("core:dashboard")


def student_id_list(request: HttpRequest) -> HttpResponse:
    grade = request.GET.get("grade")
    qs = Student.objects.filter(is_active=True).only("student_code", "nickname", "full_name", "grade_level")
    if grade:
        qs = qs.filter(grade_level=grade)
    students = qs.order_by("grade_level", "student_code")
    return render(request, "core/student_id_list.html", {"students": students, "selected_grade": grade})


# ─────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────

TIME_SLOT_ORDER = [
    TutoringClass.TimeSlot.SAT_MORNING,
    TutoringClass.TimeSlot.SAT_AFTERNOON,
    TutoringClass.TimeSlot.SUN_MORNING,
    TutoringClass.TimeSlot.SUN_AFTERNOON,
]


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    selected_date = _parse_date(request.GET.get("date"))
    classes = TutoringClass.objects.filter(is_active=True).order_by("name").all()

    classes_by_time_slot = OrderedDict()
    for ts in TIME_SLOT_ORDER:
        classes_by_time_slot[ts] = {"label": TutoringClass.TimeSlot(ts).label, "classes": []}
    for cls in classes:
        if cls.time_slot in classes_by_time_slot:
            classes_by_time_slot[cls.time_slot]["classes"].append(cls)

    enrollments = (
        Enrollment.objects.select_related("student", "tutoring_class")
        .filter(is_active=True, student__is_active=True, tutoring_class__is_active=True)
        .order_by("tutoring_class__name", "student__nickname", "student__full_name", "student__grade_level")
    )

    todays_att = Attendance.objects.filter(attendance_date=selected_date)
    att_map = {a.enrollment_id: a for a in todays_att}

    summary_by_class_id = {}
    seats_summary_by_class_id = {}
    global_present = global_excused = global_no_show = global_total = 0
    slot_totals: dict[str, dict[str, int]] = {ts: {"present": 0, "excused": 0, "no_show": 0, "total": 0} for ts in TIME_SLOT_ORDER}

    for cls in classes:
        cls_enrollments = enrollments.filter(tutoring_class=cls)
        enrollment_count = cls_enrollments.count()
        atts = todays_att.filter(enrollment__in=cls_enrollments)
        present = atts.filter(status=Attendance.Status.PRESENT).count()
        excused = atts.filter(status=Attendance.Status.EXCUSED).count()
        no_show = atts.filter(status=Attendance.Status.NO_SHOW).count()
        summary_by_class_id[cls.id] = {"present": present, "excused": excused, "no_show": no_show, "total": present + excused + no_show}
        seats_total = cls.total_seats or 0
        seats_available = max(seats_total - enrollment_count, 0)
        seats_summary_by_class_id[cls.id] = {"seats_total": seats_total, "seats_in_progress": enrollment_count, "seats_available": seats_available}
        global_present += present
        global_excused += excused
        global_no_show += no_show
        global_total += present + excused + no_show
        if cls.time_slot in slot_totals:
            slot_totals[cls.time_slot]["present"] += present
            slot_totals[cls.time_slot]["excused"] += excused
            slot_totals[cls.time_slot]["no_show"] += no_show
            slot_totals[cls.time_slot]["total"] += (present + excused + no_show)

    global_summary = {"present": global_present, "excused": global_excused, "no_show": global_no_show, "total": global_total}

    other_day_date: date | None = None
    other_day_summary: dict | None = None
    two_day_summary: dict | None = None
    wd = selected_date.weekday()
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

    return render(request, "core/dashboard.html", {
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
        "TIME_SLOT_ORDER": TIME_SLOT_ORDER,
    })


# ─────────────────────────────────────────
# Export Excel
# ─────────────────────────────────────────

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
    ws1.append(["Enrollment ID", "Student Code", "Nickname", "Full Name", "Grade", "Class", "Sessions Total", "Remaining Sessions", "Is Active", "Created At"])
    enrollments = Enrollment.objects.select_related("student", "tutoring_class").order_by("-is_active", "tutoring_class__name", "student__nickname", "student__full_name")
    for e in enrollments:
        s = e.student
        c = e.tutoring_class
        ws1.append([e.id, getattr(s, "student_code", "") or "", getattr(s, "nickname", "") or "", getattr(s, "full_name", "") or "", getattr(s, "grade_level", "") or "", getattr(c, "name", "") or "", getattr(e, "sessions_total", "") or "", getattr(e, "remaining_sessions", "") if getattr(e, "remaining_sessions", None) is not None else "", bool(getattr(e, "is_active", False)), e.created_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(e, "created_at", None) else ""])
    _autosize(ws1)
    buff = BytesIO()
    wb.save(buff)
    buff.seek(0)
    filename = f"pkanoon_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    resp = HttpResponse(buff.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


# ─────────────────────────────────────────
# Attendance
# ─────────────────────────────────────────

@require_POST
@login_required
def attendance_submit(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    selected_date = _parse_date(payload.get("date"))
    class_id = payload.get("class_id")
    items = payload.get("items", [])
    if not class_id:
        return JsonResponse({"ok": False, "error": "Missing class_id"}, status=400)

    valid_status = {Attendance.Status.PRESENT, Attendance.Status.EXCUSED, Attendance.Status.NO_SHOW}
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

    enrollments = Enrollment.objects.select_related("student", "tutoring_class").filter(tutoring_class_id=class_id, is_active=True, student__is_active=True, tutoring_class__is_active=True).all()
    enroll_map = {e.id: e for e in enrollments}

    already_checked_ids = set(Attendance.objects.filter(attendance_date=selected_date, enrollment__tutoring_class_id=class_id, student__is_active=True).values_list("enrollment_id", flat=True))
    required_ids = set(enroll_map.keys()) - already_checked_ids
    submitted_ids = {it["enrollment_id"] for it in normalized_items}
    missing = sorted(list(required_ids - submitted_ids))
    if missing:
        return JsonResponse({"ok": False, "error": "กรุณาเลือกสถานะให้ครบทุกคนในห้องนี้ก่อนกด Submit", "missing_enrollment_ids": missing}, status=400)

    now = timezone.now()
    with transaction.atomic():
        for it in normalized_items:
            eid = it["enrollment_id"]
            status = it["status"]
            e = enroll_map.get(eid)
            if not e:
                continue
            att, _ = Attendance.objects.get_or_create(student=e.student, enrollment=e, attendance_date=selected_date, defaults={"status": status})
            att.status = status
            att.checked_at = now
            att.save()

    cls_summary = Attendance.objects.filter(attendance_date=selected_date, enrollment__tutoring_class_id=class_id, student__is_active=True).aggregate(present=Count("id", filter=Q(status=Attendance.Status.PRESENT)), excused=Count("id", filter=Q(status=Attendance.Status.EXCUSED)), no_show=Count("id", filter=Q(status=Attendance.Status.NO_SHOW)), total=Count("id"))
    global_summary = Attendance.objects.filter(attendance_date=selected_date, enrollment__tutoring_class__is_active=True, student__is_active=True).aggregate(present=Count("id", filter=Q(status=Attendance.Status.PRESENT)), excused=Count("id", filter=Q(status=Attendance.Status.EXCUSED)), no_show=Count("id", filter=Q(status=Attendance.Status.NO_SHOW)), total=Count("id"))
    refreshed = Enrollment.objects.filter(id__in=list(enroll_map.keys())).only("id", "sessions_total")
    remaining_map = {e.id: e.remaining_sessions for e in refreshed}
    submitted_eids = [it["enrollment_id"] for it in normalized_items]
    checked_at_qs = Attendance.objects.filter(attendance_date=selected_date, enrollment_id__in=submitted_eids).only("enrollment_id", "checked_at")
    checked_at_map = {a.enrollment_id: _fmt_dt_th(a.checked_at) for a in checked_at_qs}

    return JsonResponse({"ok": True, "class_id": int(class_id), "date": selected_date.isoformat(), "class_summary": cls_summary, "global_summary": global_summary, "remaining_map": remaining_map, "checked_at_map": checked_at_map, "server_now_text": _fmt_dt_th(now)})


@login_required
def alerts_dashboard(request: HttpRequest) -> HttpResponse:
    THRESHOLD = 2
    enrollments = Enrollment.objects.select_related("student", "tutoring_class").filter(student__is_active=True, tutoring_class__is_active=True).order_by("tutoring_class__name", "student__nickname", "student__full_name", "student__grade_level").all()
    near = [e for e in enrollments if (e.remaining_sessions or 0) < THRESHOLD]
    return render(request, "core/alerts_dashboard.html", {"near": near, "threshold": THRESHOLD})


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
    qs = Attendance.objects.select_related("student").filter(attendance_date__gte=start_date, attendance_date__lte=end_date, student__is_active=True).only("attendance_date", "student_id")
    for a in qs:
        ws = a.attendance_date - timedelta(days=a.attendance_date.weekday())
        if ws in buckets:
            buckets[ws].add(a.student_id)
    labels = [ws.strftime("%d %b") for ws in week_starts]
    counts = [len(buckets[ws]) for ws in week_starts]
    max_count = max(counts) if counts else 0
    return render(request, "core/admin_dashboard.html", {"labels": labels, "counts": counts, "max_count": max_count, "weeks": weeks})


@login_required
def attendance_details(request: HttpRequest) -> HttpResponse:
    classes = TutoringClass.objects.filter(is_active=True).order_by("name").all()
    enrollments = Enrollment.objects.select_related("student", "tutoring_class").filter(is_active=True, student__is_active=True, tutoring_class__is_active=True).order_by("tutoring_class__name", "student__nickname", "student__full_name", "student__grade_level").all()
    all_att = Attendance.objects.filter(enrollment__in=enrollments).only("enrollment_id", "attendance_date", "status", "checked_at").order_by("attendance_date", "checked_at").all()
    att_list_map: dict[int, list[dict]] = {e.id: [] for e in enrollments}
    for a in all_att:
        att_list_map[a.enrollment_id].append({"date": a.attendance_date, "status": a.status})
    grouped_rows: dict[int, list[dict]] = {}
    for e in enrollments:
        recs = att_list_map.get(e.id, [])
        present_cnt = sum(1 for r in recs if r.get("status") == Attendance.Status.PRESENT)
        excused_cnt = sum(1 for r in recs if r.get("status") == Attendance.Status.EXCUSED)
        noshow_cnt = sum(1 for r in recs if r.get("status") == Attendance.Status.NO_SHOW)
        grouped_rows.setdefault(e.tutoring_class_id, []).append({"enrollment": e, "records": recs[:22], "present_cnt": present_cnt, "excused_cnt": excused_cnt, "noshow_cnt": noshow_cnt, "total_sessions": int(getattr(e, "sessions_total", 0) or 0), "remaining_sessions": int(getattr(e, "remaining_sessions", 0) or 0)})
    return render(request, "core/attendance_details.html", {"classes": classes, "grouped_rows": grouped_rows, "session_cols": list(range(1, 23))})


# ─────────────────────────────────────────
# Student Portal
# ─────────────────────────────────────────

class StudentPortalLoginForm(forms.Form):
    student_id = forms.CharField(label="เลือกชื่อน้อง", required=True, widget=forms.Select(attrs={"id": "id_student_id"}))
    parent_phone = forms.CharField(label="เบอร์ผู้ปกครอง", max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student_id"].widget.choices = [("", "พิมพ์ค้นหาชื่อเล่น / ชื่อจริง / รหัสนักเรียน")]

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
    q = (request.GET.get("q") or "").strip()
    qs = Student.objects.filter(is_active=True)
    if q:
        qs = qs.filter(Q(nickname__icontains=q) | Q(full_name__icontains=q) | Q(student_code__icontains=q))
    qs = qs.only("id", "student_code", "nickname", "full_name", "grade_level").order_by("grade_level", "student_code")[:30]
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
    enrollments = Enrollment.objects.select_related("tutoring_class").filter(student=student).order_by("-is_active", "-created_at").all()
    selected_enrollment_id = request.GET.get("enrollment_id")
    selected_enrollment = None
    if selected_enrollment_id:
        selected_enrollment = enrollments.filter(id=selected_enrollment_id).first()
    if not selected_enrollment and enrollments:
        selected_enrollment = enrollments[0]
    attendance_rows = []
    if selected_enrollment:
        attendance_rows = Attendance.objects.filter(student=student, enrollment=selected_enrollment).order_by("-attendance_date", "-checked_at").all()
    remaining_sessions = selected_enrollment.remaining_sessions if selected_enrollment else 0
    hours_per_session = float(selected_enrollment.tutoring_class.hours_per_session) if selected_enrollment else 0.0
    remaining_hours = remaining_sessions * hours_per_session
    return render(request, "core/student_portal_home.html", {"student": student, "enrollments": enrollments, "selected_enrollment": selected_enrollment, "attendance_rows": attendance_rows, "remaining_sessions": remaining_sessions, "hours_per_session": hours_per_session, "remaining_hours": remaining_hours})


@login_required
def generate_course_notice(request: HttpRequest) -> HttpResponse:
    enrollment_id = request.GET.get("enrollment_id") or request.POST.get("enrollment_id")
    if not enrollment_id:
        return render(request, "core/generate_course_notice.html", {"error": "missing enrollment_id"})
    enrollment = get_object_or_404(Enrollment.objects.select_related("student", "tutoring_class"), id=enrollment_id, is_active=True, student__is_active=True, tutoring_class__is_active=True)
    student = enrollment.student
    tutoring_class = enrollment.tutoring_class
    base_price = enrollment.course_price if getattr(enrollment, "course_price", None) is not None else (tutoring_class.course_price if tutoring_class else 0)

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
    amount_10 = to_decimal(request.POST.get("amount_10") if request.method == "POST" else None, Decimal(str(base_price or 0)))
    discount_10 = to_decimal(request.POST.get("discount_10") if request.method == "POST" else None, Decimal("0"))
    net_10 = max(amount_10 - discount_10, Decimal("0"))
    amount_20_default = Decimal(str(base_price or 0)) * 2
    amount_20 = to_decimal(request.POST.get("amount_20") if request.method == "POST" else None, amount_20_default)
    discount_20 = to_decimal(request.POST.get("discount_20") if request.method == "POST" else None, Decimal("0"))
    net_20 = max(amount_20 - discount_20, Decimal("0"))
    return render(request, "core/generate_course_notice.html", {"student": student, "enrollment": enrollment, "tutoring_class": tutoring_class, "remaining_sessions": enrollment.remaining_sessions, "course_end_date": course_end_date, "next_course_start_date": next_course_start_date, "amount_10": amount_10, "discount_10": discount_10, "net_10": net_10, "amount_20": amount_20, "discount_20": discount_20, "net_20": net_20, "qr_promptpay_static": "core/img/qr_promptpay.png", "qr_line_static": "core/img/qr_line.png"})


# =============================================================
# QUIZ — Helper
# =============================================================

def _get_ordered_quizzes(grade: str) -> list:
    quizzes = list(Quiz.objects.filter(grade_level=grade, is_active=True))

    def sort_key(q):
        try:
            return SUBJECT_DISPLAY_ORDER.index(q.subject_name)
        except ValueError:
            return 99

    return sorted(quizzes, key=sort_key)


# =============================================================
# QUIZ — Public views
# =============================================================

def quiz_grade_select(request: HttpRequest) -> HttpResponse:
    grades_with_quizzes = list(
        Quiz.objects.filter(is_active=True).values_list("grade_level", flat=True).distinct()
    )
    return render(request, "core/quiz_grade_select.html", {
        "grade_choices": GRADE_CHOICES,
        "grades_with_quizzes": grades_with_quizzes,
    })


def quiz_register(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        grade = request.GET.get("grade", "")
        if not grade:
            return redirect("core:quiz_grade_select")

        # AJAX → ส่ง JSON รายวิชา
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            quizzes = _get_ordered_quizzes(grade)
            return JsonResponse({"subjects": [q.subject_name for q in quizzes]})

        # ปกติ → หน้า register
        quizzes = _get_ordered_quizzes(grade)
        if not quizzes:
            grades_with_quizzes = list(Quiz.objects.filter(is_active=True).values_list("grade_level", flat=True).distinct())
            return render(request, "core/quiz_grade_select.html", {
                "grade_choices": GRADE_CHOICES,
                "grades_with_quizzes": grades_with_quizzes,
                "error": f"ยังไม่มีข้อสอบสำหรับ {grade} กรุณาติดต่อพี่ขนุน",
            })
        return render(request, "core/quiz_register.html", {
            "grade": grade,
            "grade_display": dict(GRADE_CHOICES).get(grade, grade),
            "quizzes": quizzes,
        })

    # POST
    grade = request.POST.get("grade", "").strip()
    nickname = request.POST.get("nickname", "").strip()
    firstname = request.POST.get("firstname", "").strip()
    lastname = request.POST.get("lastname", "").strip()
    school = request.POST.get("school", "").strip()
    email = request.POST.get("email", "").strip()

    if not grade or not nickname or not firstname or not lastname or not school:
        quizzes = _get_ordered_quizzes(grade)
        return render(request, "core/quiz_register.html", {
            "grade": grade,
            "grade_display": dict(GRADE_CHOICES).get(grade, grade),
            "quizzes": quizzes,
            "error": "กรุณากรอกข้อมูลให้ครบ (ชื่อเล่น / ชื่อจริง / นามสกุล / โรงเรียน)",
            "prev": request.POST,
        })

    session_key = secrets.token_urlsafe(24)
    request.session["quiz_taker"] = {
        "grade": grade, "nickname": nickname, "firstname": firstname,
        "lastname": lastname, "school": school, "email": email,
        "session_key": session_key,
    }

    quizzes = _get_ordered_quizzes(grade)
    if not quizzes:
        return redirect("core:quiz_grade_select")
    return redirect("core:quiz_take", quiz_id=quizzes[0].id)


def quiz_take(request: HttpRequest, quiz_id: int) -> HttpResponse:
    taker = request.session.get("quiz_taker")
    if not taker:
        return redirect("core:quiz_grade_select")

    quiz = get_object_or_404(Quiz, pk=quiz_id, is_active=True)
    if quiz.grade_level != taker["grade"]:
        return redirect("core:quiz_grade_select")

    session_key = taker["session_key"]

    # ถ้าทำวิชานี้ไปแล้ว → ไปถัดไป
    existing = QuizAttempt.objects.filter(session_key=session_key, quiz=quiz).first()
    if existing and existing.status == QuizAttempt.Status.SUBMITTED:
        return _next_quiz_redirect(taker, quiz, session_key)

    # สร้าง attempt
    if not existing:
        existing = QuizAttempt.objects.create(
            taker_nickname=taker["nickname"],
            taker_firstname=taker["firstname"],
            taker_lastname=taker["lastname"],
            taker_school=taker.get("school", ""),
            taker_grade=taker["grade"],
            taker_email=taker.get("email", ""),
            quiz=quiz,
            session_key=session_key,
            status=QuizAttempt.Status.IN_PROGRESS,
        )

    attempt = existing

    # ตรวจหมดเวลา
    if quiz.time_limit_minutes > 0:
        elapsed_min = (timezone.now() - attempt.started_at).total_seconds() / 60
        if elapsed_min > quiz.time_limit_minutes:
            attempt.calculate_and_save()
            return _next_quiz_redirect(taker, quiz, session_key)

    questions = list(quiz.questions.prefetch_related("choices").order_by("order"))
    questions_json = []
    for q in questions:
        choices_data = []
        for i, c in enumerate(q.choices.all()):
            choices_data.append({
                "id": c.id, "label": c.label or chr(65 + i),
                "text": c.text, "image": c.image.url if c.image else None,
            })
        questions_json.append({
            "id": q.id, "order": q.order, "type": q.question_type,
            "text": q.text, "image": q.image.url if q.image else None,
            "score": q.score, "choices": choices_data,
        })

    all_quizzes = _get_ordered_quizzes(taker["grade"])
    quiz_index = next((i for i, q in enumerate(all_quizzes) if q.id == quiz_id), 0)

    remaining_sec = 0
    if quiz.time_limit_minutes > 0:
        elapsed = (timezone.now() - attempt.started_at).total_seconds()
        remaining_sec = max(0, int(quiz.time_limit_minutes * 60 - elapsed))

    return render(request, "core/quiz_take.html", {
        "quiz": quiz, "attempt": attempt, "taker": taker,
        "questions_json": json.dumps(questions_json, ensure_ascii=False),
        "total_questions": len(questions),
        "all_quizzes": all_quizzes, "quiz_index": quiz_index,
        "remaining_sec": remaining_sec,
    })


def _next_quiz_redirect(taker, current_quiz, session_key):
    all_quizzes = _get_ordered_quizzes(taker["grade"])
    idx = next((i for i, q in enumerate(all_quizzes) if q.id == current_quiz.id), 0)
    if idx + 1 < len(all_quizzes):
        return redirect("core:quiz_take", quiz_id=all_quizzes[idx + 1].id)
    return redirect("core:quiz_result", session_key=session_key)


@require_POST
def quiz_submit(request: HttpRequest, attempt_id: int) -> JsonResponse:
    taker = request.session.get("quiz_taker")
    if not taker:
        return JsonResponse({"ok": False, "error": "session expired"}, status=403)

    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, session_key=taker["session_key"], status=QuizAttempt.Status.IN_PROGRESS)
    data = json.loads(request.body)
    answers = data.get("answers", {})

    with transaction.atomic():
        QuizAnswer.objects.filter(attempt=attempt).delete()
        for q_id_str, choice_ids in answers.items():
            try:
                question = Question.objects.get(pk=int(q_id_str), quiz=attempt.quiz)
            except Question.DoesNotExist:
                continue
            for c_id in choice_ids:
                try:
                    choice = Choice.objects.get(pk=int(c_id), question=question)
                    QuizAnswer.objects.create(attempt=attempt, question=question, choice=choice)
                except Choice.DoesNotExist:
                    continue
        attempt.calculate_and_save()

    all_quizzes = _get_ordered_quizzes(taker["grade"])
    idx = next((i for i, q in enumerate(all_quizzes) if q.id == attempt.quiz_id), 0)
    if idx + 1 < len(all_quizzes):
        redirect_url = f"/quiz/take/{all_quizzes[idx + 1].id}/"
    else:
        redirect_url = f"/quiz/result/{taker['session_key']}/"

    return JsonResponse({"ok": True, "redirect": redirect_url})


def quiz_result(request: HttpRequest, session_key: str) -> HttpResponse:
    attempts = (
        QuizAttempt.objects
        .filter(session_key=session_key, status=QuizAttempt.Status.SUBMITTED)
        .select_related("quiz")
        .order_by("quiz__subject_name")
    )
    if not attempts.exists():
        return redirect("core:quiz_grade_select")

    first = attempts.first()

    def attempt_sort(a):
        try:
            return SUBJECT_DISPLAY_ORDER.index(a.quiz.subject_name)
        except ValueError:
            return 99

    sorted_attempts = sorted(attempts, key=attempt_sort)
    total_score = sum(float(a.score) for a in sorted_attempts)
    total_max = sum(float(a.max_score) for a in sorted_attempts)
    total_percent = round(total_score / total_max * 100, 1) if total_max else 0

    attempt_details = []
    for att in sorted_attempts:
        questions = att.quiz.questions.prefetch_related("choices").order_by("order")
        answered_map = {}
        for ans in QuizAnswer.objects.filter(attempt=att).select_related("question", "choice"):
            answered_map.setdefault(ans.question_id, []).append(ans.choice_id)
        attempt_details.append({"attempt": att, "questions": list(questions), "answered_map": answered_map})

    return render(request, "core/quiz_result.html", {
        "session_key": session_key, "sorted_attempts": sorted_attempts,
        "attempt_details": attempt_details, "first": first,
        "total_score": total_score, "total_max": total_max, "total_percent": total_percent,
    })


@require_POST
def quiz_send_pdf(request: HttpRequest, session_key: str) -> JsonResponse:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
    except ImportError:
        return JsonResponse({"ok": False, "error": "กรุณาติดตั้ง: pip install reportlab"})

    attempts = QuizAttempt.objects.filter(session_key=session_key, status=QuizAttempt.Status.SUBMITTED).select_related("quiz")
    if not attempts.exists():
        return JsonResponse({"ok": False, "error": "ไม่พบข้อมูลการสอบ"})

    first = attempts.first()
    email_to = (request.POST.get("email") or first.taker_email or "").strip()
    if not email_to:
        return JsonResponse({"ok": False, "error": "กรุณาระบุอีเมลที่ต้องการรับผลสอบ"})

    def attempt_sort(a):
        try:
            return SUBJECT_DISPLAY_ORDER.index(a.quiz.subject_name)
        except ValueError:
            return 99

    sorted_attempts = sorted(attempts, key=attempt_sort)
    total_score = sum(float(a.score) for a in sorted_attempts)
    total_max = sum(float(a.max_score) for a in sorted_attempts)
    total_pct = round(total_score / total_max * 100, 1) if total_max else 0

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("t", parent=styles["Heading1"], fontSize=20, spaceAfter=4, textColor=colors.HexColor("#0f172a"))
    sub_style = ParagraphStyle("s", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#475569"), spaceAfter=3)
    story.append(Paragraph("ผลการทดสอบออนไลน์", title_style))
    story.append(Paragraph("พี่ขนุนติวเตอร์ | P'Kanoon E-Pretest", sub_style))
    story.append(Spacer(1, 0.3*cm))

    info_data = [
        ["ชื่อเล่น", first.taker_nickname, "ชื่อ-สกุล", first.taker_full_name],
        ["ระดับชั้น", first.taker_grade, "โรงเรียน", first.taker_school or "-"],
        ["วันที่สอบ", first.submitted_at.strftime("%d/%m/%Y %H:%M") if first.submitted_at else "-", "", ""],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 5.5*cm, 3*cm, 5.5*cm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#64748b")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#64748b")),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4*cm))

    table_data = [["วิชา", "ชุดข้อสอบ", "ได้", "เต็ม", "%", "ผล"]]
    for a in sorted_attempts:
        table_data.append([a.quiz.subject_name, a.quiz.title[:30], str(int(a.score)), str(int(a.max_score)), f"{a.score_percent}%", "✓ ผ่าน" if a.passed else "✗ ไม่ผ่าน"])
    table_data.append(["รวมทุกวิชา", "", str(int(total_score)), str(int(total_max)), f"{total_pct}%", ""])

    t = Table(table_data, colWidths=[3.5*cm, 5*cm, 2*cm, 2*cm, 2*cm, 2.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fdd35e")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"คะแนนรวม: {int(total_score)}/{int(total_max)} = {total_pct}%", ParagraphStyle("big", parent=styles["Normal"], fontSize=14, textColor=colors.HexColor("#0f172a"))))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("ขอบคุณที่ใช้บริการพี่ขนุนติวเตอร์ | Line: @pkanoontutor", sub_style))
    doc.build(story)
    buf.seek(0)

    try:
        email_msg = EmailMessage(
            subject=f"ผลข้อสอบ P'Kanoon E-Pretest – {first.taker_nickname} ({first.taker_grade})",
            body=f"สวัสดีครับ/ค่ะ {first.taker_nickname}\n\nผลการสอบของ {first.taker_full_name} ชั้น {first.taker_grade}\nคะแนนรวม: {int(total_score)}/{int(total_max)} = {total_pct}%\n\nติดต่อ Line: @pkanoontutor\n\nพี่ขนุนติวเตอร์",
            from_email="pkanoontutor@gmail.com",
            to=[email_to],
        )
        email_msg.attach(f"quiz_result_{first.taker_nickname}.pdf", buf.read(), "application/pdf")
        email_msg.send(fail_silently=False)
        return JsonResponse({"ok": True, "message": f"ส่งผลสอบไปที่ {email_to} แล้วครับ ✉️"})
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"ส่งอีเมลไม่สำเร็จ: {str(e)}"})


# =============================================================
# QUIZ ADMIN
# =============================================================

@login_required
def quiz_admin_list(request: HttpRequest) -> HttpResponse:
    grade_filter = request.GET.get("grade", "")
    subject_filter = request.GET.get("subject", "")
    quizzes = Quiz.objects.order_by("grade_level", "subject_name", "title")
    if grade_filter:
        quizzes = quizzes.filter(grade_level=grade_filter)
    if subject_filter:
        quizzes = quizzes.filter(subject_name__icontains=subject_filter)
    for q in quizzes:
        q.total_q = q.total_questions()
        q.total_s = q.total_score()
        q.attempt_count = q.attempts.filter(status=QuizAttempt.Status.SUBMITTED).count()
    subject_names = list(Quiz.objects.values_list("subject_name", flat=True).distinct().order_by("subject_name"))
    return render(request, "core/quiz_admin_list.html", {
        "quizzes": quizzes, "grade_choices": GRADE_CHOICES,
        "subject_names": subject_names, "grade_filter": grade_filter, "subject_filter": subject_filter,
    })


@login_required
def quiz_admin_create(request: HttpRequest) -> HttpResponse:
    error = None
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        subject_name = request.POST.get("subject_name", "").strip()
        grade = request.POST.get("grade_level", "")
        description = request.POST.get("description", "")
        time_limit = int(request.POST.get("time_limit_minutes", 0) or 0)
        pass_score = int(request.POST.get("pass_score", 60) or 60)
        is_active = request.POST.get("is_active") == "on"
        if title and subject_name and grade:
            quiz = Quiz.objects.create(title=title, subject_name=subject_name, grade_level=grade, description=description, time_limit_minutes=time_limit, pass_score=pass_score, is_active=is_active)
            return redirect("core:quiz_admin_edit", quiz_id=quiz.id)
        error = "กรุณากรอกข้อมูลให้ครบ"
    return render(request, "core/quiz_admin_form.html", {"quiz": None, "grade_choices": GRADE_CHOICES, "error": error})


@login_required
def quiz_admin_edit(request: HttpRequest, quiz_id: int) -> HttpResponse:
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    error = None
    if request.method == "POST":
        title = request.POST.get("title", quiz.title).strip()
        if not title:
            error = "กรุณากรอกชื่อชุดข้อสอบ"
        else:
            quiz.title = title
            quiz.subject_name = request.POST.get("subject_name", quiz.subject_name).strip() or quiz.subject_name
            quiz.grade_level = request.POST.get("grade_level", quiz.grade_level)
            quiz.description = request.POST.get("description", "")
            quiz.time_limit_minutes = int(request.POST.get("time_limit_minutes", 0) or 0)
            quiz.pass_score = int(request.POST.get("pass_score", 60) or 60)
            quiz.is_active = request.POST.get("is_active") == "on"
            quiz.save()
            return redirect("core:quiz_admin_edit", quiz_id=quiz.id)
    questions = quiz.questions.prefetch_related("choices").order_by("order")
    return render(request, "core/quiz_admin_form.html", {"quiz": quiz, "questions": questions, "grade_choices": GRADE_CHOICES, "error": error})


@login_required
@require_POST
def quiz_admin_toggle(request: HttpRequest, quiz_id: int) -> HttpResponse:
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    quiz.is_active = not quiz.is_active
    quiz.save()
    return redirect("core:quiz_admin_list")


@login_required
@require_POST
def quiz_admin_delete(request: HttpRequest, quiz_id: int) -> HttpResponse:
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    quiz.delete()
    return redirect("core:quiz_admin_list")


@login_required
def quiz_question_add(request: HttpRequest, quiz_id: int) -> HttpResponse:
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    error = None
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if not text:
            error = "กรุณากรอกข้อความคำถาม"
        else:
            question = Question.objects.create(quiz=quiz, order=quiz.questions.count() + 1, question_type=request.POST.get("question_type", "single"), text=text, score=int(request.POST.get("score", 1) or 1), explanation=request.POST.get("explanation", ""))
            if "image" in request.FILES:
                question.image = request.FILES["image"]
                question.save()
            labels = request.POST.getlist("choice_label")
            texts = request.POST.getlist("choice_text")
            corrects = request.POST.getlist("choice_correct")
            for i, (lbl, txt) in enumerate(zip(labels, texts)):
                if not txt.strip():
                    continue
                Choice.objects.create(question=question, label=lbl or chr(65 + i), text=txt.strip(), is_correct=(str(i) in corrects), order=i + 1)
            return redirect("core:quiz_admin_edit", quiz_id=quiz.id)
    return render(request, "core/quiz_question_form.html", {"quiz": quiz, "question": None, "error": error})


@login_required
def quiz_question_edit(request: HttpRequest, question_id: int) -> HttpResponse:
    question = get_object_or_404(Question, pk=question_id)
    quiz = question.quiz
    error = None
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if not text:
            error = "กรุณากรอกข้อความคำถาม"
        else:
            question.question_type = request.POST.get("question_type", question.question_type)
            question.text = text
            question.score = int(request.POST.get("score", 1) or 1)
            question.explanation = request.POST.get("explanation", "")
            question.order = int(request.POST.get("order", question.order) or question.order)
            if "image" in request.FILES:
                question.image = request.FILES["image"]
            question.save()
            question.choices.all().delete()
            labels = request.POST.getlist("choice_label")
            texts = request.POST.getlist("choice_text")
            corrects = request.POST.getlist("choice_correct")
            for i, (lbl, txt) in enumerate(zip(labels, texts)):
                if not txt.strip():
                    continue
                Choice.objects.create(question=question, label=lbl or chr(65 + i), text=txt.strip(), is_correct=(str(i) in corrects), order=i + 1)
            return redirect("core:quiz_admin_edit", quiz_id=quiz.id)
    return render(request, "core/quiz_question_form.html", {"quiz": quiz, "question": question, "choices": question.choices.order_by("order"), "error": error})


@login_required
@require_POST
def quiz_question_delete(request: HttpRequest, question_id: int) -> HttpResponse:
    question = get_object_or_404(Question, pk=question_id)
    quiz_id = question.quiz_id
    question.delete()
    return redirect("core:quiz_admin_edit", quiz_id=quiz_id)


# =============================================================
# QUIZ REPORT
# =============================================================

@login_required
def quiz_report(request: HttpRequest) -> HttpResponse:
    qs = QuizAttempt.objects.filter(status=QuizAttempt.Status.SUBMITTED).select_related("quiz").order_by("-submitted_at")
    grade_f = request.GET.get("grade", "")
    subject_f = request.GET.get("subject", "")
    name_f = request.GET.get("name", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if grade_f:
        qs = qs.filter(taker_grade=grade_f)
    if subject_f:
        qs = qs.filter(quiz__subject_name__icontains=subject_f)
    if name_f:
        qs = qs.filter(Q(taker_nickname__icontains=name_f) | Q(taker_firstname__icontains=name_f) | Q(taker_lastname__icontains=name_f))
    if date_from:
        try:
            qs = qs.filter(submitted_at__date__gte=date.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(submitted_at__date__lte=date.fromisoformat(date_to))
        except ValueError:
            pass
    total_count = qs.count()
    subject_names = list(Quiz.objects.values_list("subject_name", flat=True).distinct().order_by("subject_name"))
    return render(request, "core/quiz_report.html", {
        "attempts": qs[:500], "total_count": total_count,
        "grade_choices": GRADE_CHOICES, "subject_names": subject_names,
        "grade_f": grade_f, "subject_f": subject_f, "name_f": name_f,
        "date_from": date_from, "date_to": date_to,
    })


@login_required
def quiz_report_export(request: HttpRequest) -> HttpResponse:
    qs = QuizAttempt.objects.filter(status=QuizAttempt.Status.SUBMITTED).select_related("quiz").order_by("-submitted_at")
    grade_f = request.GET.get("grade", "")
    subject_f = request.GET.get("subject", "")
    name_f = request.GET.get("name", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if grade_f:
        qs = qs.filter(taker_grade=grade_f)
    if subject_f:
        qs = qs.filter(quiz__subject_name__icontains=subject_f)
    if name_f:
        qs = qs.filter(Q(taker_nickname__icontains=name_f) | Q(taker_firstname__icontains=name_f) | Q(taker_lastname__icontains=name_f))
    if date_from:
        try:
            qs = qs.filter(submitted_at__date__gte=date.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(submitted_at__date__lte=date.fromisoformat(date_to))
        except ValueError:
            pass
    wb = Workbook()
    ws = wb.active
    ws.title = "Quiz Report"
    ws.append(["ชื่อเล่น", "ชื่อจริง", "นามสกุล", "โรงเรียน", "ระดับชั้น", "วิชา", "ชุดข้อสอบ", "คะแนนที่ได้", "คะแนนเต็ม", "%", "ผ่าน", "วันที่ส่ง"])
    for a in qs:
        ws.append([a.taker_nickname, a.taker_firstname, a.taker_lastname, a.taker_school, a.taker_grade, a.quiz.subject_name, a.quiz.title, float(a.score), float(a.max_score), f"{a.score_percent}%", "ผ่าน" if a.passed else "ไม่ผ่าน", a.submitted_at.strftime("%Y-%m-%d %H:%M") if a.submitted_at else ""])
    _autosize(ws)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="quiz_report.xlsx"'
    return resp
