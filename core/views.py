from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta

from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Student,
    Attendance,
    Enrollment,
    TutoringClass,
    ClassSubject,
    Sheet,
    SheetUpdateEntry,  # ✅ ใหม่: ใช้เก็บ Sheet Update แบบรายวัน
    SheetInventory,
)


def _parse_date(s: str | None) -> date:
    if not s:
        return timezone.localdate()
    try:
        return date.fromisoformat(s)
    except ValueError:
        return timezone.localdate()


def home_redirect(request: HttpRequest) -> HttpResponse:
    # หน้าแรกให้ไป dashboard ใหม่
    return redirect("core:dashboard")


# -----------------------
# ✅ Dashboard (ข้อ C)
# - ฝั่งขวาใช้ข้อมูลจาก "SheetUpdateEntry ของวันที่ล่าสุดที่หยอด"
# -----------------------
@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """
    หน้าเดียว:
    - ซ้าย: เช็คชื่อ (ทุกห้องทุกคน เรียงตามคลาส) แต่ submit แยกทีละห้อง
    - ขวา: ความคืบหน้าชีท (ใช้ข้อมูลจาก Sheet Update วันที่ล่าสุดที่มีการบันทึก)
    """
    selected_date = _parse_date(request.GET.get("date"))

    classes = TutoringClass.objects.filter(is_active=True).order_by("name").all()

    # Enrollment เรียงตาม: คลาส -> ชื่อเล่น -> ชื่อจริง -> ระดับชั้น
    enrollments = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(is_active=True, student__is_active=True, tutoring_class__is_active=True)
        .order_by(
            "tutoring_class__name",
            "student__nickname",
            "student__full_name",
            "student__grade_level",
        )
        .all()
    )

    # ✅ Course order per student (คอร์สลำดับที่)
    student_ids = list({e.student_id for e in enrollments})
    all_enrollments_for_students = (
        Enrollment.objects
        .filter(student_id__in=student_ids)
        .order_by("student_id", "created_at", "id")
        .values("id", "student_id")
    )

    course_seq_by_enrollment_id: dict[int, int] = {}
    course_total_by_student: dict[int, int] = {}
    current_sid: int | None = None
    seq = 0
    for row in all_enrollments_for_students:
        sid = int(row["student_id"])
        if sid != current_sid:
            current_sid = sid
            seq = 0
        seq += 1
        eid = int(row["id"])
        course_seq_by_enrollment_id[eid] = seq
        course_total_by_student[sid] = seq

    # Attendance ของวันนั้น (เอามาโชว์สถานะที่เคย submit แล้ว)
    todays_att = (
        Attendance.objects
        .select_related("enrollment", "student")
        .filter(attendance_date=selected_date)
        .all()
    )
    att_map = {a.enrollment_id: a for a in todays_att}

    # Summary ต่อ class (วันนี้)
    class_summaries = (
        Attendance.objects
        .filter(attendance_date=selected_date, enrollment__tutoring_class__is_active=True, student__is_active=True)
        .values("enrollment__tutoring_class_id")
        .annotate(
            present=Count("id", filter=Q(status=Attendance.Status.PRESENT)),
            excused=Count("id", filter=Q(status=Attendance.Status.EXCUSED)),
            no_show=Count("id", filter=Q(status=Attendance.Status.NO_SHOW)),
            total=Count("id"),
        )
    )
    summary_by_class_id = {row["enrollment__tutoring_class_id"]: row for row in class_summaries}

    # Summary รวมทั้งหมด (วันนี้)
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

    # -----------------------
    # ✅ (ข้อ C) ด้านขวา: sheet progress จาก "SheetUpdateEntry วันที่ล่าสุด"
    # -----------------------
    sheet_latest_date = (
        SheetUpdateEntry.objects
        .order_by("-date")
        .values_list("date", flat=True)
        .first()
    )

    # grouped_subjects ต้องคงชื่อเดิมเพื่อใช้กับ dashboard.html ของคุณ
    # และต้องมี field ตามที่ template ใช้: subject, current_sheet, current_page, current_question, progress_percent
    grouped_subjects: dict[int, list[dict]] = {}

    if sheet_latest_date:
        latest_entries = (
            SheetUpdateEntry.objects
            .select_related("tutoring_class", "subject", "sheet")
            .filter(date=sheet_latest_date, tutoring_class__is_active=True, subject__is_active=True)
            .order_by("tutoring_class__name", "subject__name")
            .all()
        )

        for e in latest_entries:
            grouped_subjects.setdefault(e.tutoring_class_id, []).append({
                "subject": e.subject,
                "current_sheet": e.sheet,  # ให้ template ใช้ชื่อเดิม
                "current_page": e.page_taught_to,
                "current_question": e.question_taught_to,
                "progress_percent": e.progress_percent(),
                "last_teacher": e.last_teacher,
            })
    else:
        # ถ้ายังไม่เคยหยอด Sheet Update เลย → ยังไม่โชว์อะไร (หรือจะ fallback ไป ClassSubject ก็ได้)
        grouped_subjects = {}

    # ใกล้ครบคอร์ส (ไว้โชว์เป็น list ฝั่งซ้าย) — น้อยกว่า 2 ครั้ง
    THRESHOLD = 2
    near_complete = []
    for e in enrollments:
        if e.remaining_sessions() < 2:
            near_complete.append(e)

    context = {
        "selected_date": selected_date,
        "classes": classes,
        "enrollments": enrollments,
        "att_map": att_map,
        "summary_by_class_id": summary_by_class_id,
        "global_summary": global_summary,

        # ✅ ฝั่งขวา
        "grouped_subjects": grouped_subjects,
        "sheet_latest_date": sheet_latest_date,  # (ถ้าคุณอยากโชว์ว่าอัปเดตล่าสุดวันไหนใน template)

        "near_complete": near_complete,
        "threshold": THRESHOLD,
        "course_seq_by_enrollment_id": course_seq_by_enrollment_id,
        "course_total_by_student": course_total_by_student,
    }
    return render(request, "core/dashboard.html", context)


# -----------------------
# ✅ Sheet Update (ข้อ 1)
# - มีเลือกวันที่ (default = วันที่ล่าสุดที่เคยหยอด)
# - ช่อง page / question / teacher เป็นช่องให้พิมพ์ (รายวัน)
# - ไม่ทับ ClassSubject
# -----------------------
class _SheetUpdateRowForm(forms.Form):
    class_subject_id = forms.IntegerField(widget=forms.HiddenInput)

    subject_name = forms.CharField(required=False, disabled=True)

    sheet = forms.ModelChoiceField(
        queryset=Sheet.objects.filter(is_active=True).order_by("subject__name", "code"),
        required=False,
        empty_label="-- เลือกชีท --",
    )
    page_taught_to = forms.IntegerField(required=False, min_value=0)
    question_taught_to = forms.IntegerField(required=False, min_value=0)
    last_teacher = forms.CharField(required=False)

    def __init__(self, *args, subject_id: int | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        # ให้ dropdown แสดงเฉพาะชีทของวิชานั้น (สวยและใช้ง่าย)
        if subject_id:
            self.fields["sheet"].queryset = Sheet.objects.filter(
                is_active=True, subject_id=subject_id
            ).order_by("code")


@login_required
def sheet_update(request: HttpRequest) -> HttpResponse:
    """
    Sheet Update แบบรายวัน:
    - เลือกวันที่ได้ (default = วันที่ล่าสุดที่เคยบันทึก)
    - แสดงเป็น section ตามคลาส (ดึงคู่คลาส/วิชาจาก ClassSubject)
    - กรอก: sheet, page_taught_to, question_taught_to, last_teacher
    - บันทึกลง SheetUpdateEntry (unique ต่อ class+subject+date)
    """

    # ✅ default date = วันที่ล่าสุดที่เคยหยอด
    latest_date = SheetUpdateEntry.objects.order_by("-date").values_list("date", flat=True).first()
    default_date = latest_date or timezone.localdate()

    # รับ date จาก GET (เปลี่ยนวันที่ดู/กรอก)
    if request.method == "GET":
        selected_date = _parse_date(request.GET.get("date")) if request.GET.get("date") else default_date
    else:
        selected_date = _parse_date(request.POST.get("date")) if request.POST.get("date") else default_date

    # แถวที่จะโชว์: ดึงจาก ClassSubject เพื่อให้ "มี class ใหม่ → section มาเอง"
    class_subjects = (
        ClassSubject.objects
        .select_related("tutoring_class", "subject")
        .filter(is_active=True, tutoring_class__is_active=True, subject__is_active=True)
        .order_by("tutoring_class__name", "subject__name")
        .all()
    )

    # โหลดค่าที่เคยกรอกของวันนั้น (prefill)
    existing = (
        SheetUpdateEntry.objects
        .select_related("sheet")
        .filter(date=selected_date)
        .all()
    )
    existing_map = {(e.tutoring_class_id, e.subject_id): e for e in existing}

    # group แบบเดิมที่ template คุณคุ้นเคย: [{class:..., forms:[...]}, ...]
    grouped: list[dict] = []

    # helper: map class_id -> dict bucket
    class_bucket: dict[int, dict] = {}

    if request.method == "POST":
        # สร้าง form ตามจำนวนแถว และ validate รวม
        rows: list[tuple[ClassSubject, _SheetUpdateRowForm]] = []
        for cs in class_subjects:
            prefix = f"cs{cs.id}"
            f = _SheetUpdateRowForm(request.POST, prefix=prefix, subject_id=cs.subject_id)
            rows.append((cs, f))

        all_valid = all(f.is_valid() for _, f in rows)

        if all_valid:
            now = timezone.now()
            with transaction.atomic():
                for cs, f in rows:
                    key = (cs.tutoring_class_id, cs.subject_id)
                    entry = existing_map.get(key)
                    if not entry:
                        entry = SheetUpdateEntry(
                            tutoring_class=cs.tutoring_class,
                            subject=cs.subject,
                            date=selected_date,
                        )

                    entry.sheet = f.cleaned_data.get("sheet")
                    entry.page_taught_to = f.cleaned_data.get("page_taught_to") or 0
                    entry.question_taught_to = f.cleaned_data.get("question_taught_to") or 0
                    entry.last_teacher = (f.cleaned_data.get("last_teacher") or "").strip()
                    entry.updated_at = now
                    entry.updated_by = request.user
                    entry.save()

            return redirect(f"/sheet-update/?date={selected_date.isoformat()}")

        # ถ้าไม่ผ่าน → render โดยยังคงค่าที่พิมพ์ไว้
        for cs, f in rows:
            cls = cs.tutoring_class
            if cls.id not in class_bucket:
                class_bucket[cls.id] = {"class": cls, "forms": []}

            # แสดง total_pages จาก sheet ที่เลือก (ถ้าเลือกแล้ว)
            chosen_sheet = f.cleaned_data.get("sheet") if f.is_bound and f.is_valid() else None
            total_pages = chosen_sheet.total_pages if chosen_sheet else 0

            class_bucket[cls.id]["forms"].append({
                "class_subject": cs,
                "form": f,
                "total_pages": total_pages,
            })

    else:
        # GET → build initial
        for cs in class_subjects:
            key = (cs.tutoring_class_id, cs.subject_id)
            entry = existing_map.get(key)

            initial = {
                "class_subject_id": cs.id,
                "subject_name": cs.subject.name,
                "sheet": entry.sheet_id if entry and entry.sheet_id else None,
                "page_taught_to": entry.page_taught_to if entry else "",
                "question_taught_to": entry.question_taught_to if entry else "",
                "last_teacher": entry.last_teacher if entry else "",
            }

            prefix = f"cs{cs.id}"
            f = _SheetUpdateRowForm(prefix=prefix, initial=initial, subject_id=cs.subject_id)

            cls = cs.tutoring_class
            if cls.id not in class_bucket:
                class_bucket[cls.id] = {"class": cls, "forms": []}

            total_pages = entry.sheet.total_pages if entry and entry.sheet else 0
            class_bucket[cls.id]["forms"].append({
                "class_subject": cs,
                "form": f,
                "total_pages": total_pages,
            })

    grouped = sorted(class_bucket.values(), key=lambda x: x["class"].name)

    return render(request, "core/sheet_update.html", {
        "grouped": grouped,              # [{class: TutoringClass, forms:[{class_subject, form, total_pages}, ...]}, ...]
        "selected_date": selected_date,  # ✅ ให้ template ใช้ใส่ value date
        "default_date": default_date,    # ✅ วันที่ล่าสุดที่เคยหยอด
    })


@require_POST
@login_required
def attendance_submit(request: HttpRequest) -> JsonResponse:
    """
    Submit แยกทีละห้อง:
    รับ JSON:
    {
      "date": "YYYY-MM-DD",
      "class_id": 123,
      "items": [
        {"enrollment_id": 1, "status": "present"},
        {"enrollment_id": 2, "status": "excused"},
        ...
      ]
    }

    หลักการ:
    - ปุ่ม 3 แบบบนหน้าเว็บ = แค่เลือก (ยังไม่หัก)
    - กด Submit = ค่อย create/update Attendance ของทั้งห้องในวันนั้น
    - ✅ บังคับ: ต้องส่งสถานะมาครบทุกคนในห้องนี้ก่อน Submit
    - ✅ แก้บั๊ก: normalize enrollment_id เป็น int เสมอ (กัน string/int mismatch)
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

    submitted_ids = {it["enrollment_id"] for it in normalized_items}
    all_ids = set(enroll_map.keys())
    missing = sorted(list(all_ids - submitted_ids))

    if missing:
        return JsonResponse({
            "ok": False,
            "error": "กรุณาเลือกสถานะให้ครบทุกคนในห้องนี้ก่อนกด Submit",
            "missing_enrollment_ids": missing,
            "debug": {
                "submitted_count": len(submitted_ids),
                "expected_count": len(all_ids),
            }
        }, status=400)

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
            att.checked_at = timezone.now()
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

    remaining_map = {eid: enroll_map[eid].remaining_sessions() for eid in enroll_map.keys()}

    return JsonResponse({
        "ok": True,
        "class_id": int(class_id),
        "date": selected_date.isoformat(),
        "class_summary": cls_summary,
        "global_summary": global_summary,
        "remaining_map": remaining_map,
    })


@login_required
def alerts_dashboard(request: HttpRequest) -> HttpResponse:
    """
    หน้า list นักเรียนที่ใกล้ครบคอร์ส + สถานะว่าแจ้งแล้วหรือยัง
    """
    THRESHOLD = 2
    enrollments = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(student__is_active=True, tutoring_class__is_active=True)
        .order_by("tutoring_class__name", "student__nickname", "student__full_name", "student__grade_level")
        .all()
    )

    near = []
    for e in enrollments:
        if e.remaining_sessions() < 2:
            near.append(e)

    return render(request, "core/alerts_dashboard.html", {
        "near": near,
        "threshold": THRESHOLD,
    })


@require_POST
@login_required
def alerts_mark(request: HttpRequest) -> HttpResponse:
    """
    ใช้ได้ทั้งจากหน้า /alerts/ และ dropdown ใน dashboard

    POST:
      - enrollment_id
      - method: "line" | "facebook" | "paper" | "" (ยังไม่แจ้ง)
    """
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
def sheet_dashboard(request: HttpRequest) -> HttpResponse:
    """
    หน้าชีทแบบเต็มหน้า (เผื่ออยากดูแยก) — dashboard หลักก็มีฝั่งขวาอยู่แล้ว
    """
    classes = TutoringClass.objects.filter(is_active=True).order_by("name").all()

    # แสดงจาก ClassSubject แบบเดิม (หน้าแยกนี้ยังใช้แบบเดิมได้)
    class_subjects = (
        ClassSubject.objects
        .select_related("tutoring_class", "subject", "current_sheet")
        .filter(is_active=True, tutoring_class__is_active=True, subject__is_active=True)
        .order_by("tutoring_class__name", "subject__name")
        .all()
    )

    grouped: dict[int, list[ClassSubject]] = {}
    for cs in class_subjects:
        grouped.setdefault(cs.tutoring_class_id, []).append(cs)

    return render(request, "core/sheet_dashboard.html", {
        "classes": classes,
        "grouped": grouped,
    })


@login_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Admin Dashboard: กราฟจำนวนนักเรียน active รายสัปดาห์ (ย้อนหลัง 8 สัปดาห์)
    นิยาม "Active รายสัปดาห์": มี Attendance record ในสัปดาห์นั้น (สถานะอะไรก็ได้)
    """
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
    Student Attendance (Details)
    - หน้าเดียวเห็นครบทุกห้องทุกคน
    - Row = นักเรียน (ตาม Enrollment)
    - Column = ครั้งที่ 1..N (ตามจำนวน Attendance ที่มีจริงในห้องนั้น)
    - Cell = วันที่ + สถานะ (มา/ลา/ขาด)
    """
    classes = TutoringClass.objects.filter(is_active=True).order_by("name").all()

    enrollments = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(student__is_active=True, tutoring_class__is_active=True)
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
    max_cols_by_class: dict[int, int] = {}

    for e in enrollments:
        recs = att_list_map.get(e.id, [])
        grouped_rows.setdefault(e.tutoring_class_id, []).append({
            "enrollment": e,
            "records": recs,
        })
        mx = max_cols_by_class.get(e.tutoring_class_id, 0)
        if len(recs) > mx:
            max_cols_by_class[e.tutoring_class_id] = len(recs)

    col_numbers_by_class: dict[int, list[int]] = {}
    for cls in classes:
        mx = max_cols_by_class.get(cls.id, 0)
        col_numbers_by_class[cls.id] = list(range(1, mx + 1))

    return render(request, "core/attendance_details.html", {
        "classes": classes,
        "grouped_rows": grouped_rows,
        "col_numbers_by_class": col_numbers_by_class,
    })


# =========================================================
# ✅ Student Portal (ผู้ปกครอง)
# - Login ด้วย: รหัสนักเรียน + เบอร์ผู้ปกครอง (ที่กรอกไว้ใน Student.parent_phone)
# - แสดง: ชั่วโมง/ครั้งคงเหลือ + ประวัติมา/ลา/ขาด (จาก Attendance)
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

        # ✅ เช็คเบอร์ (normalize แบบง่าย: เอาแต่ตัวเลข)
        def digits(x: str) -> str:
            return "".join(ch for ch in x if ch.isdigit())

        if digits(student.parent_phone) != digits(phone):
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

    # enrollments ของนักเรียน (active ก่อน)
    enrollments = (
        Enrollment.objects
        .select_related("tutoring_class")
        .filter(student=student)
        .order_by("-is_active", "-created_at")
        .all()
    )

    # เลือก enrollment ที่ดูรายละเอียด (default: ตัวแรก)
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

    # คำนวณชั่วโมงคงเหลือจาก enrollment ที่เลือก (ถ้าไม่มี enrollment ก็เป็น 0)
    remaining_sessions = selected_enrollment.remaining_sessions() if selected_enrollment else 0
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
# ✅ Sheet Inventory
# - แสดงชีทคงเหลือเรียงตาม code (A-Z)
# - มี action: เพิ่ม/ลด/แก้ไขเลขโดยตรง/จบชีท (ย้ายไปส่วน "ชีทที่จบแล้ว")
# =========================================================
@require_POST
@login_required
def _sheet_inventory_action(request: HttpRequest) -> HttpResponse:
    action = (request.POST.get("action") or "").strip()
    item_id = request.POST.get("item_id")

    if not item_id:
        return redirect("core:sheet_inventory")

    item = get_object_or_404(SheetInventory, id=item_id)

    with transaction.atomic():
        item = SheetInventory.objects.select_for_update().get(id=item.id)

        if action == "inc":
            item.quantity += 1
        elif action == "dec":
            item.quantity -= 1
        elif action == "set":
            try:
                item.quantity = int(request.POST.get("quantity") or 0)
            except Exception:
                item.quantity = item.quantity
        elif action == "finish":
            item.is_finished = True
        elif action == "unfinish":
            item.is_finished = False

        item.save()

    return redirect("core:sheet_inventory")


@login_required
def sheet_inventory(request: HttpRequest) -> HttpResponse:
    # ✅ ensure ทุก Sheet มี inventory record (เฉพาะที่ยังไม่มี)
    sheets = Sheet.objects.filter(is_active=True).select_related("subject").order_by("code").all()
    existing_ids = set(SheetInventory.objects.values_list("sheet_id", flat=True))
    to_create = [SheetInventory(sheet=s, quantity=0, is_finished=False) for s in sheets if s.id not in existing_ids]
    if to_create:
        SheetInventory.objects.bulk_create(to_create)

    active_items = (
        SheetInventory.objects
        .select_related("sheet", "sheet__subject")
        .filter(is_finished=False, sheet__is_active=True)
        .order_by("sheet__code")
        .all()
    )

    finished_items = (
        SheetInventory.objects
        .select_related("sheet", "sheet__subject")
        .filter(is_finished=True)
        .order_by("sheet__code")
        .all()
    )

    if request.method == "POST":
        # route action ผ่าน helper เพื่อให้ template ง่าย
        return _sheet_inventory_action(request)

    context = {
        "active_items": active_items,
        "finished_items": finished_items,
    }
    return render(request, "core/sheet_inventory.html", context)
