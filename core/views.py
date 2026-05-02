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
    Student,
    Attendance,
    Enrollment,
    TutoringClass,
    Subject,
    Quiz,
    Question,
    Choice,
    QuizAttempt,
    QuizAnswer,
    GRADE_CHOICES,
    SUBJECT_DISPLAY_ORDER,
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
    grade = request.GET.get("grade")
    qs = Student.objects.filter(is_active=True).only("student_code", "nickname", "full_name", "grade_level")
    if grade:
        qs = qs.filter(grade_level=grade)
    students = qs.order_by("grade_level", "student_code")
    return render(request, "core/student_id_list.html", {"students": students, "selected_grade": grade})


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
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(is_active=True, student__is_active=True, tutoring_class__is_active=True)
        .order_by("tutoring_class__name", "student__nickname", "student__full_name", "student__grade_level")
    )

    todays_att = Attendance.objects.filter(attendance_date=selected_date)
    att_map = {a.enrollment_id: a for a in todays_att}

    summary_by_class_id = {}
    seats_summary_by_class_id = {}
    global_present = global_excused = global_no_show = global_total = 0
    slot_totals: dict[str, dict[str, int]] = {
        ts: {"present": 0, "excused": 0, "no_show": 0, "total": 0} for ts in TIME_SLOT_ORDER
    }

    for cls in classes:
        cls_enrollments = enrollments.filter(tutoring_class=cls)
        enrollment_count = cls_enrollments.count()
        atts = todays_att.filter(enrollment__in=cls_enrollments)
        present = atts.filter(status=Attendance.Status.PRESENT).count()
        excused = atts.filter(status=Attendance.Status.EXCUSED).count()
        no_show = atts.filter(status=Attendance.Status.NO_SHOW).count()
        summary_by_class_id[cls.id] = {"present": present, "excused": excused, "no_show": no_show, "total": present + excused + no_show}
        seats_total = cls.total_seats or 0
        seats_in_progress = enrollment_count
        seats_available = max(seats_total - seats_in_progress, 0)
        seats_summary_by_class_id[cls.id] = {"seats_total": seats_total, "seats_in_progress": seats_in_progress, "seats_available": seats_available}
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
        other_day_atts = Attendance.objects.filter(attendance_date=other_day_date)
        op = other_day_atts.filter(status=Attendance.Status.PRESENT).count()
        oe = other_day_atts.filter(status=Attendance.Status.EXCUSED).count()
        ons = other_day_atts.filter(status=Attendance.Status.NO_SHOW).count()
        other_day_summary = {"present": op, "excused": oe, "no_show": ons, "total": op + oe + ons}
        two_day_summary = {
            "present": global_present + op, "excused": global_excused + oe,
            "no_show": global_no_show + ons, "total": global_total + op + oe + ons,
        }

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
        "TIME_SLOT_ORDER": TIME_SLOT_ORDER,
        "other_day_date": other_day_date,
        "other_day_summary": other_day_summary,
        "two_day_summary": two_day_summary,
    })


@login_required
@require_POST
def attendance_submit(request: HttpRequest) -> JsonResponse:
    data = json.loads(request.body)
    att_date = _parse_date(data.get("date"))
    records = data.get("records", [])
    results = []
    for rec in records:
        enrollment_id = rec.get("enrollment_id")
        status = rec.get("status")
        if not enrollment_id or not status:
            continue
        try:
            enrollment = Enrollment.objects.select_related("student").get(id=enrollment_id, is_active=True)
        except Enrollment.DoesNotExist:
            continue
        att, created = Attendance.objects.get_or_create(
            student=enrollment.student,
            enrollment=enrollment,
            attendance_date=att_date,
            defaults={"status": status},
        )
        if not created:
            att.status = status
            att.checked_at = timezone.now()
            att.save()
        results.append({"enrollment_id": enrollment_id, "status": att.status, "ok": True})
    return JsonResponse({"ok": True, "results": results})


@login_required
def alerts_dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "core/alerts_dashboard.html", {})


@login_required
@require_POST
def alerts_mark(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True})


@login_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "core/admin_dashboard.html", {})


@login_required
def attendance_details(request: HttpRequest) -> HttpResponse:
    classes = TutoringClass.objects.filter(is_active=True).order_by("name")
    enrollments = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(is_active=True, student__is_active=True, tutoring_class__is_active=True)
        .order_by("tutoring_class__name", "student__nickname", "student__full_name", "student__grade_level")
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
        att_list_map[a.enrollment_id].append({"date": a.attendance_date, "status": a.status})
    grouped_rows: dict[int, list[dict]] = {}
    for e in enrollments:
        recs = att_list_map.get(e.id, [])
        present_cnt = sum(1 for r in recs if r.get("status") == Attendance.Status.PRESENT)
        excused_cnt = sum(1 for r in recs if r.get("status") == Attendance.Status.EXCUSED)
        noshow_cnt = sum(1 for r in recs if r.get("status") == Attendance.Status.NO_SHOW)
        grouped_rows.setdefault(e.tutoring_class_id, []).append({
            "enrollment": e, "records": recs[:22],
            "present_cnt": present_cnt, "excused_cnt": excused_cnt, "noshow_cnt": noshow_cnt,
            "total_sessions": int(getattr(e, "sessions_total", 0) or 0),
            "remaining_sessions": int(getattr(e, "remaining_sessions", 0) or 0),
        })
    session_cols = list(range(1, 23))
    return render(request, "core/attendance_details.html", {"classes": classes, "grouped_rows": grouped_rows, "session_cols": session_cols})


# =========================================================
# Student Portal
# =========================================================
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
        attendance_rows = Attendance.objects.filter(student=student, enrollment=selected_enrollment).order_by("-attendance_date", "-checked_at").all()
    remaining_sessions = selected_enrollment.remaining_sessions if selected_enrollment else 0
    hours_per_session = float(selected_enrollment.tutoring_class.hours_per_session) if selected_enrollment else 0.0
    remaining_hours = remaining_sessions * hours_per_session
    context = {
        "student": student, "enrollments": enrollments,
        "selected_enrollment": selected_enrollment, "attendance_rows": attendance_rows,
        "remaining_sessions": remaining_sessions, "hours_per_session": hours_per_session, "remaining_hours": remaining_hours,
    }
    return render(request, "core/student_portal_home.html", context)


@login_required
def generate_course_notice(request: HttpRequest) -> HttpResponse:
    enrollment_id = request.GET.get("enrollment_id") or request.POST.get("enrollment_id")
    if not enrollment_id:
        return render(request, "core/generate_course_notice.html", {"error": "missing enrollment_id"})
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "tutoring_class"),
        id=enrollment_id, is_active=True, student__is_active=True, tutoring_class__is_active=True,
    )
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
    context = {
        "student": student, "enrollment": enrollment, "tutoring_class": tutoring_class,
        "remaining_sessions": enrollment.remaining_sessions, "course_end_date": course_end_date,
        "next_course_start_date": next_course_start_date, "amount_10": amount_10,
        "discount_10": discount_10, "net_10": net_10, "amount_20": amount_20,
        "discount_20": discount_20, "net_20": net_20,
        "qr_promptpay_static": "core/img/qr_promptpay.png",
        "qr_line_static": "core/img/qr_line.png",
    }
    return render(request, "core/generate_course_notice.html", context)


@login_required
def export_excel(request: HttpRequest) -> HttpResponse:
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"
    headers = ["Student Code", "Nickname", "Full Name", "Grade", "School", "Phone", "Active"]
    ws.append(headers)
    for s in Student.objects.select_related("school").order_by("student_code"):
        ws.append([s.student_code, s.nickname, s.full_name, s.grade_level, s.school.name if s.school else "", s.parent_phone, "Yes" if s.is_active else "No"])
    for i, col in enumerate(ws.columns, 1):
        ws.column_dimensions[get_column_letter(i)].width = 20
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="students.xlsx"'
    return resp


# =========================================================
# QUIZ — helper
# =========================================================

def _get_ordered_quizzes(grade: str) -> list:
    quizzes = list(Quiz.objects.filter(grade_level=grade, is_active=True).select_related("subject"))

    def sort_key(q):
        try:
            return SUBJECT_DISPLAY_ORDER.index(q.subject.name)
        except ValueError:
            return 99

    return sorted(quizzes, key=sort_key)


# =========================================================
# QUIZ — Public views
# =========================================================

def quiz_grade_select(request: HttpRequest) -> HttpResponse:
    """หน้าเลือกระดับชั้น"""
    grades_with_quizzes = (
        Quiz.objects.filter(is_active=True)
        .values_list("grade_level", flat=True)
        .distinct()
    )
    return render(request, "core/quiz_grade_select.html", {
        "grade_choices": GRADE_CHOICES,
        "grades_with_quizzes": list(grades_with_quizzes),
    })


def quiz_register(request: HttpRequest) -> HttpResponse:
    """กรอกข้อมูลผู้สอบ → เริ่มสอบ"""
    if request.method == "GET":
        grade = request.GET.get("grade", "")
        if not grade:
            return redirect("core:quiz_grade_select")
        # ตรวจว่ามี quiz ในระดับนี้ไหม
        quizzes = _get_ordered_quizzes(grade)
        if not quizzes:
            return render(request, "core/quiz_grade_select.html", {
                "grade_choices": GRADE_CHOICES,
                "grades_with_quizzes": list(Quiz.objects.filter(is_active=True).values_list("grade_level", flat=True).distinct()),
                "error": f"ยังไม่มีข้อสอบสำหรับ {grade} กรุณาติดต่อพี่ขนุน",
            })
        return render(request, "core/quiz_register.html", {
            "grade": grade,
            "grade_display": dict(GRADE_CHOICES).get(grade, grade),
            "quizzes": quizzes,
        })

    # POST → บันทึก session แล้วไปข้อสอบวิชาแรก
    grade = request.POST.get("grade", "").strip()
    nickname = request.POST.get("nickname", "").strip()
    firstname = request.POST.get("firstname", "").strip()
    lastname = request.POST.get("lastname", "").strip()
    school = request.POST.get("school", "").strip()
    email = request.POST.get("email", "").strip()

    if not grade or not nickname or not firstname or not lastname:
        quizzes = _get_ordered_quizzes(grade)
        return render(request, "core/quiz_register.html", {
            "grade": grade,
            "grade_display": dict(GRADE_CHOICES).get(grade, grade),
            "quizzes": quizzes,
            "error": "กรุณากรอกข้อมูลให้ครบ (ชื่อเล่น / ชื่อจริง / นามสกุล)",
            "prev": request.POST,
        })

    session_key = secrets.token_urlsafe(24)
    request.session["quiz_taker"] = {
        "grade": grade,
        "nickname": nickname,
        "firstname": firstname,
        "lastname": lastname,
        "school": school,
        "email": email,
        "session_key": session_key,
    }

    quizzes = _get_ordered_quizzes(grade)
    if not quizzes:
        return redirect("core:quiz_grade_select")
    return redirect("core:quiz_take", quiz_id=quizzes[0].id)


def quiz_take(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """หน้าทำข้อสอบ interactive ทีละข้อ"""
    taker = request.session.get("quiz_taker")
    if not taker:
        return redirect("core:quiz_grade_select")

    quiz = get_object_or_404(Quiz, pk=quiz_id, is_active=True)

    if quiz.grade_level != taker["grade"]:
        return redirect("core:quiz_grade_select")

    session_key = taker["session_key"]

    # ถ้าทำวิชานี้ไปแล้วให้ข้ามไปวิชาถัดไปหรือผลสอบ
    existing = QuizAttempt.objects.filter(session_key=session_key, quiz=quiz).first()
    if existing and existing.status == QuizAttempt.Status.SUBMITTED:
        return _next_quiz_redirect(taker, quiz, session_key)

    # สร้าง attempt ใหม่ (หรือใช้อันที่ค้างอยู่)
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
            attempt.status = QuizAttempt.Status.TIMED_OUT
            attempt.submitted_at = timezone.now()
            attempt.calculate_and_save()
            return _next_quiz_redirect(taker, quiz, session_key)

    questions = list(quiz.questions.prefetch_related("choices").order_by("order"))

    questions_json = []
    for q in questions:
        choices_data = []
        for i, c in enumerate(q.choices.all()):
            choices_data.append({
                "id": c.id,
                "label": c.label or chr(65 + i),  # A, B, C, D
                "text": c.text,
                "image": c.image.url if c.image else None,
            })
        questions_json.append({
            "id": q.id,
            "order": q.order,
            "type": q.question_type,
            "text": q.text,
            "image": q.image.url if q.image else None,
            "score": q.score,
            "choices": choices_data,
        })

    all_quizzes = _get_ordered_quizzes(taker["grade"])
    quiz_index = next((i for i, q in enumerate(all_quizzes) if q.id == quiz_id), 0)

    # คำนวณ remaining seconds
    remaining_sec = 0
    if quiz.time_limit_minutes > 0:
        elapsed = (timezone.now() - attempt.started_at).total_seconds()
        remaining_sec = max(0, int(quiz.time_limit_minutes * 60 - elapsed))

    return render(request, "core/quiz_take.html", {
        "quiz": quiz,
        "attempt": attempt,
        "taker": taker,
        "questions_json": json.dumps(questions_json, ensure_ascii=False),
        "total_questions": len(questions),
        "all_quizzes": all_quizzes,
        "quiz_index": quiz_index,
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

    attempt = get_object_or_404(
        QuizAttempt,
        pk=attempt_id,
        session_key=taker["session_key"],
        status=QuizAttempt.Status.IN_PROGRESS,
    )

    data = json.loads(request.body)
    answers = data.get("answers", {})  # {"question_id": [choice_id, ...]}

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

    session_key = taker["session_key"]
    all_quizzes = _get_ordered_quizzes(taker["grade"])
    idx = next((i for i, q in enumerate(all_quizzes) if q.id == attempt.quiz_id), 0)

    if idx + 1 < len(all_quizzes):
        redirect_url = f"/quiz/take/{all_quizzes[idx + 1].id}/"
    else:
        redirect_url = f"/quiz/result/{session_key}/"

    return JsonResponse({"ok": True, "redirect": redirect_url})


def quiz_result(request: HttpRequest, session_key: str) -> HttpResponse:
    """หน้าผลสอบรวม"""
    attempts = (
        QuizAttempt.objects
        .filter(session_key=session_key, status=QuizAttempt.Status.SUBMITTED)
        .select_related("quiz__subject")
        .order_by("quiz__subject__name")
    )
    if not attempts.exists():
        return redirect("core:quiz_grade_select")

    first = attempts.first()

    def attempt_sort(a):
        try:
            return SUBJECT_DISPLAY_ORDER.index(a.quiz.subject.name)
        except ValueError:
            return 99

    sorted_attempts = sorted(attempts, key=attempt_sort)
    total_score = sum(float(a.score) for a in sorted_attempts)
    total_max = sum(float(a.max_score) for a in sorted_attempts)
    total_percent = round(total_score / total_max * 100, 1) if total_max else 0

    # ดึง answers สำหรับ review
    attempt_details = []
    for att in sorted_attempts:
        questions = att.quiz.questions.prefetch_related("choices").order_by("order")
        answered_map = {}
        for ans in QuizAnswer.objects.filter(attempt=att).select_related("question", "choice"):
            answered_map.setdefault(ans.question_id, []).append(ans.choice_id)
        attempt_details.append({
            "attempt": att,
            "questions": list(questions),
            "answered_map": answered_map,
        })

    return render(request, "core/quiz_result.html", {
        "session_key": session_key,
        "sorted_attempts": sorted_attempts,
        "attempt_details": attempt_details,
        "first": first,
        "total_score": total_score,
        "total_max": total_max,
        "total_percent": total_percent,
    })


@require_POST
def quiz_send_pdf(request: HttpRequest, session_key: str) -> JsonResponse:
    """สร้าง PDF แล้วส่งอีเมล Gmail"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
    except ImportError:
        return JsonResponse({"ok": False, "error": "กรุณาติดตั้ง: pip install reportlab"})

    attempts = (
        QuizAttempt.objects
        .filter(session_key=session_key, status=QuizAttempt.Status.SUBMITTED)
        .select_related("quiz__subject")
        .order_by("quiz__subject__name")
    )
    if not attempts.exists():
        return JsonResponse({"ok": False, "error": "ไม่พบข้อมูลการสอบ"})

    first = attempts.first()
    email_to = (request.POST.get("email") or first.taker_email or "").strip()
    if not email_to:
        return JsonResponse({"ok": False, "error": "กรุณาระบุอีเมลที่ต้องการรับผลสอบ"})

    def attempt_sort(a):
        try:
            return SUBJECT_DISPLAY_ORDER.index(a.quiz.subject.name)
        except ValueError:
            return 99

    sorted_attempts = sorted(attempts, key=attempt_sort)
    total_score = sum(float(a.score) for a in sorted_attempts)
    total_max = sum(float(a.max_score) for a in sorted_attempts)
    total_pct = round(total_score / total_max * 100, 1) if total_max else 0

    # Build PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("t", parent=styles["Heading1"], fontSize=20, spaceAfter=4, textColor=colors.HexColor("#0f172a"))
    sub_style = ParagraphStyle("s", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#475569"), spaceAfter=3)
    story.append(Paragraph("ผลการทดสอบออนไลน์", title_style))
    story.append(Paragraph("พี่ขนุนติวเตอร์  |  pkanoontutor.com", sub_style))
    story.append(Spacer(1, 0.3*cm))

    # Taker info
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

    # Score table
    table_data = [["วิชา", "ข้อสอบ", "คะแนนที่ได้", "คะแนนเต็ม", "%", "ผล"]]
    for a in sorted_attempts:
        table_data.append([
            a.quiz.subject.name,
            a.quiz.title[:30],
            str(int(a.score)),
            str(int(a.max_score)),
            f"{a.score_percent}%",
            "✓ ผ่าน" if a.passed else "✗ ไม่ผ่าน",
        ])
    table_data.append(["รวมทุกวิชา", "", str(int(total_score)), str(int(total_max)), f"{total_pct}%", ""])

    t = Table(table_data, colWidths=[3.5*cm, 5*cm, 2.5*cm, 2.5*cm, 2*cm, 2.5*cm])
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
            subject=f"ผลข้อสอบออนไลน์ – {first.taker_nickname} ({first.taker_grade}) | พี่ขนุนติวเตอร์",
            body=(
                f"สวัสดีครับ/ค่ะ คุณ {first.taker_nickname}\n\n"
                f"ขอบคุณที่ทำแบบทดสอบออนไลน์กับพี่ขนุนติวเตอร์นะครับ\n"
                f"ผลการสอบของ {first.taker_full_name} ระดับชั้น {first.taker_grade} แนบมาในไฟล์ PDF ด้านล่างนี้เลยครับ\n\n"
                f"คะแนนรวม: {int(total_score)}/{int(total_max)} = {total_pct}%\n\n"
                f"หากสนใจติวกับพี่ขนุนติวเตอร์ ติดต่อ Line: @pkanoontutor\n\n"
                f"พี่ขนุนติวเตอร์"
            ),
            from_email="pkanoontutor@gmail.com",
            to=[email_to],
        )
        email_msg.attach(
            f"quiz_result_{first.taker_nickname}_{first.taker_grade}.pdf",
            buf.read(),
            "application/pdf",
        )
        email_msg.send(fail_silently=False)
        return JsonResponse({"ok": True, "message": f"ส่งผลสอบไปที่ {email_to} แล้วครับ ✉️"})
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"ส่งอีเมลไม่สำเร็จ: {str(e)}"})


# =========================================================
# QUIZ ADMIN (ต้อง login Django)
# =========================================================

@login_required
def quiz_admin_list(request: HttpRequest) -> HttpResponse:
    grade_filter = request.GET.get("grade", "")
    subject_filter = request.GET.get("subject", "")
    quizzes = Quiz.objects.select_related("subject").order_by("grade_level", "subject__name", "title")
    if grade_filter:
        quizzes = quizzes.filter(grade_level=grade_filter)
    if subject_filter:
        quizzes = quizzes.filter(subject__id=subject_filter)
    subjects = Subject.objects.filter(is_active=True).order_by("name")
    # สถิติ
    for q in quizzes:
        q._total_q = q.total_questions()
        q._total_s = q.total_score()
        q._attempt_count = q.attempts.filter(status=QuizAttempt.Status.SUBMITTED).count()
    return render(request, "core/quiz_admin_list.html", {
        "quizzes": quizzes,
        "grade_choices": GRADE_CHOICES,
        "subjects": subjects,
        "grade_filter": grade_filter,
        "subject_filter": subject_filter,
    })


@login_required
def quiz_admin_create(request: HttpRequest) -> HttpResponse:
    subjects = Subject.objects.filter(is_active=True).order_by("name")
    error = None
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        subject_id = request.POST.get("subject_id", "")
        grade = request.POST.get("grade_level", "")
        description = request.POST.get("description", "")
        time_limit = int(request.POST.get("time_limit_minutes", 0) or 0)
        pass_score = int(request.POST.get("pass_score", 60) or 60)
        is_active = request.POST.get("is_active") == "on"
        if title and subject_id and grade:
            quiz = Quiz.objects.create(
                title=title, subject_id=int(subject_id), grade_level=grade,
                description=description, time_limit_minutes=time_limit,
                pass_score=pass_score, is_active=is_active,
            )
            return redirect("core:quiz_admin_edit", quiz_id=quiz.id)
        error = "กรุณากรอกข้อมูลให้ครบ"
    return render(request, "core/quiz_admin_form.html", {
        "quiz": None, "subjects": subjects, "grade_choices": GRADE_CHOICES, "error": error,
    })


@login_required
def quiz_admin_edit(request: HttpRequest, quiz_id: int) -> HttpResponse:
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    subjects = Subject.objects.filter(is_active=True).order_by("name")
    error = None
    if request.method == "POST":
        title = request.POST.get("title", quiz.title).strip()
        sid = request.POST.get("subject_id", "")
        grade = request.POST.get("grade_level", quiz.grade_level)
        if not title:
            error = "กรุณากรอกชื่อชุดข้อสอบ"
        else:
            quiz.title = title
            if sid:
                quiz.subject_id = int(sid)
            quiz.grade_level = grade
            quiz.description = request.POST.get("description", "")
            quiz.time_limit_minutes = int(request.POST.get("time_limit_minutes", 0) or 0)
            quiz.pass_score = int(request.POST.get("pass_score", 60) or 60)
            quiz.is_active = request.POST.get("is_active") == "on"
            quiz.save()
            return redirect("core:quiz_admin_edit", quiz_id=quiz.id)
    questions = quiz.questions.prefetch_related("choices").order_by("order")
    return render(request, "core/quiz_admin_form.html", {
        "quiz": quiz, "questions": questions,
        "subjects": subjects, "grade_choices": GRADE_CHOICES, "error": error,
    })


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
            q_type = request.POST.get("question_type", "single")
            score = int(request.POST.get("score", 1) or 1)
            explanation = request.POST.get("explanation", "")
            order = quiz.questions.count() + 1
            question = Question.objects.create(
                quiz=quiz, order=order, question_type=q_type,
                text=text, score=score, explanation=explanation,
            )
            if "image" in request.FILES:
                question.image = request.FILES["image"]
                question.save()
            # choices
            labels = request.POST.getlist("choice_label")
            texts = request.POST.getlist("choice_text")
            corrects = request.POST.getlist("choice_correct")
            for i, (lbl, txt) in enumerate(zip(labels, texts)):
                if not txt.strip():
                    continue
                Choice.objects.create(
                    question=question, label=lbl or chr(65 + i),
                    text=txt.strip(), is_correct=(str(i) in corrects), order=i + 1,
                )
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
                Choice.objects.create(
                    question=question, label=lbl or chr(65 + i),
                    text=txt.strip(), is_correct=(str(i) in corrects), order=i + 1,
                )
            return redirect("core:quiz_admin_edit", quiz_id=quiz.id)
    return render(request, "core/quiz_question_form.html", {
        "quiz": quiz, "question": question,
        "choices": question.choices.order_by("order"), "error": error,
    })


@login_required
@require_POST
def quiz_question_delete(request: HttpRequest, question_id: int) -> HttpResponse:
    question = get_object_or_404(Question, pk=question_id)
    quiz_id = question.quiz_id
    question.delete()
    return redirect("core:quiz_admin_edit", quiz_id=quiz_id)


# =========================================================
# QUIZ REPORT
# =========================================================

@login_required
def quiz_report(request: HttpRequest) -> HttpResponse:
    qs = (
        QuizAttempt.objects
        .filter(status=QuizAttempt.Status.SUBMITTED)
        .select_related("quiz__subject")
        .order_by("-submitted_at")
    )
    grade_f = request.GET.get("grade", "")
    subject_f = request.GET.get("subject", "")
    name_f = request.GET.get("name", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if grade_f:
        qs = qs.filter(taker_grade=grade_f)
    if subject_f:
        qs = qs.filter(quiz__subject__id=subject_f)
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

    subjects = Subject.objects.filter(is_active=True).order_by("name")
    total_count = qs.count()
    attempts = qs[:500]

    return render(request, "core/quiz_report.html", {
        "attempts": attempts, "total_count": total_count,
        "grade_choices": GRADE_CHOICES, "subjects": subjects,
        "grade_f": grade_f, "subject_f": subject_f, "name_f": name_f,
        "date_from": date_from, "date_to": date_to,
    })


@login_required
def quiz_report_export(request: HttpRequest) -> HttpResponse:
    qs = (
        QuizAttempt.objects
        .filter(status=QuizAttempt.Status.SUBMITTED)
        .select_related("quiz__subject")
        .order_by("-submitted_at")
    )
    grade_f = request.GET.get("grade", "")
    subject_f = request.GET.get("subject", "")
    name_f = request.GET.get("name", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if grade_f:
        qs = qs.filter(taker_grade=grade_f)
    if subject_f:
        qs = qs.filter(quiz__subject__id=subject_f)
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
        ws.append([
            a.taker_nickname, a.taker_firstname, a.taker_lastname, a.taker_school, a.taker_grade,
            a.quiz.subject.name, a.quiz.title, float(a.score), float(a.max_score),
            f"{a.score_percent}%", "ผ่าน" if a.passed else "ไม่ผ่าน",
            a.submitted_at.strftime("%Y-%m-%d %H:%M") if a.submitted_at else "",
        ])
    for i, col in enumerate(ws.columns, 1):
        ws.column_dimensions[get_column_letter(i)].width = 18
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="quiz_report.xlsx"'
    return resp
