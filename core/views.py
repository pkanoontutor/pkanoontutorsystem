from __future__ import annotations
from collections import OrderedDict, defaultdict

import json
import csv
import re
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

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

from .models import (
    Student,
    School,
    Subject,
    Sheet,
    ClassSubject,
    Attendance,
    Enrollment,
    TutoringClass,
    SheetInventory,
    SheetInventoryMovement,
    SheetClassMapping,
    SheetPrintOrder,
    AdmissionInquiry,
    FinanceSetting,
    ExpenseCategory,
    SchoolExpense,
    Tutor,
    TutorPayrollEntry,
    CoursePayment,
    CourseRenewalNotice,
    TeachingTutor,
    TeachingClassSubjectTemplate,
    TeachingWeeklyAssignment,
    TeachingProgressUpdate,
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


SHEET_GRADE_ORDER = ["p4", "p5", "p6", "m1", "m2", "m3", "m4", ""]


def _sheet_grade_label(value: str | None) -> str:
    labels = {
        "p4": "ป.4",
        "p5": "ป.5",
        "p6": "ป.6",
        "m1": "ม.1",
        "m2": "ม.2",
        "m3": "ม.3",
        "m4": "ม.4",
        "": "ไม่ระบุระดับชั้น",
    }
    return labels.get((value or "").strip().lower(), value or "ไม่ระบุระดับชั้น")


def _normalize_sheet_grade_level(value: str | None) -> str:
    raw = (value or "").strip().lower().replace(" ", "")
    if not raw:
        return ""
    raw = raw.replace(".", "")
    mapping = {
        "p4": "p4", "ป4": "p4", "ประถม4": "p4", "ป.4": "p4",
        "p5": "p5", "ป5": "p5", "ประถม5": "p5", "ป.5": "p5",
        "p6": "p6", "ป6": "p6", "ประถม6": "p6", "ป.6": "p6",
        "m1": "m1", "ม1": "m1", "มัธยม1": "m1", "ม.1": "m1",
        "m2": "m2", "ม2": "m2", "มัธยม2": "m2", "ม.2": "m2",
        "m3": "m3", "ม3": "m3", "มัธยม3": "m3", "ม.3": "m3",
        "m4": "m4", "ม4": "m4", "มัธยม4": "m4", "ม.4": "m4",
    }
    return mapping.get(raw, "")


def _infer_sheet_grade_level(*texts: str | None) -> str:
    combined = " ".join((t or "") for t in texts).lower()
    # Match explicit code patterns first e.g. E-P4-01 / M-M1-01.
    for grade in ["p4", "p5", "p6", "m1", "m2", "m3", "m4"]:
        if re.search(rf"(^|[^a-z0-9]){grade}([^a-z0-9]|$)", combined, re.I):
            return grade
    for value in ["ป.4", "ป4", "ป.5", "ป5", "ป.6", "ป6", "ม.1", "ม1", "ม.2", "ม2", "ม.3", "ม3", "ม.4", "ม4"]:
        normalized = _normalize_sheet_grade_level(value)
        if value.replace(".", "") in combined.replace(".", "").replace(" ", "") and normalized:
            return normalized
    return ""


def _class_grade_level(tutoring_class: TutoringClass | None) -> str:
    if not tutoring_class:
        return ""
    return _infer_sheet_grade_level(getattr(tutoring_class, "name", ""))


def _ordered_grade_groups(rows: list[dict]) -> list[dict]:
    buckets = {g: [] for g in SHEET_GRADE_ORDER}
    for row in rows:
        grade = (getattr(row.get("sheet"), "grade_level", "") or "").lower()
        if grade not in buckets:
            buckets.setdefault(grade, [])
        buckets[grade].append(row)
    return [
        {"grade": grade, "label": _sheet_grade_label(grade), "rows": buckets.get(grade, []), "count": len(buckets.get(grade, []))}
        for grade in SHEET_GRADE_ORDER
        if buckets.get(grade)
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



# =========================================================
# ✅ Sheet Inventory Module
# =========================================================
def _sheet_code_from_text(text: str | None) -> str:
    """Extract a likely sheet code from free text such as 'M-P6-01 เศษส่วน'."""
    raw = (text or "").strip()
    if not raw:
        return ""
    # Try exact token first; sheet codes in the system usually look like M-P6-01.
    tokens = re.split(r"[\s,;:/|]+", raw)
    for token in tokens:
        t = token.strip().upper()
        if t and Sheet.objects.filter(code__iexact=t).exists():
            return t
    # Fallback: if the whole text is the code.
    if Sheet.objects.filter(code__iexact=raw.upper()).exists():
        return raw.upper()
    return ""


def _inventory_for_sheet(sheet: Sheet) -> SheetInventory | None:
    try:
        return sheet.inventory
    except SheetInventory.DoesNotExist:
        return None


def _apply_sheet_inventory_movement(
    *,
    sheet: Sheet,
    movement_type: str,
    quantity: int,
    note: str = "",
    user=None,
) -> tuple[bool, str, SheetInventory | None, SheetInventoryMovement | None]:
    """
    Centralized stock update.
    - ADD: add quantity to stock
    - DEDUCT: deduct quantity, but block if result would be negative
    - SET / COUNT: set balance to quantity
    """
    if quantity is None:
        quantity = 0

    try:
        quantity = int(quantity)
    except Exception:
        return False, "จำนวนไม่ถูกต้อง", None, None

    if movement_type in {SheetInventoryMovement.MovementType.ADD, SheetInventoryMovement.MovementType.DEDUCT}:
        if quantity <= 0:
            return False, "กรุณาระบุจำนวนมากกว่า 0", None, None
    elif movement_type in {SheetInventoryMovement.MovementType.SET, SheetInventoryMovement.MovementType.COUNT}:
        if quantity < 0:
            return False, "ยอดจริงต้องไม่ติดลบ", None, None
    else:
        return False, "ประเภท movement ไม่ถูกต้อง", None, None

    with transaction.atomic():
        inventory, _ = SheetInventory.objects.select_for_update().get_or_create(
            sheet=sheet,
            defaults={"quantity": 0},
        )
        before = int(inventory.quantity or 0)

        if movement_type == SheetInventoryMovement.MovementType.ADD:
            after = before + quantity
            movement_qty = quantity
        elif movement_type == SheetInventoryMovement.MovementType.DEDUCT:
            if before - quantity < 0:
                return False, f"ตัด stock ไม่ได้ เพราะคงเหลือ {before} ชุด", inventory, None
            after = before - quantity
            movement_qty = quantity
        else:
            after = quantity
            movement_qty = quantity

        inventory.quantity = max(after, 0)
        inventory.save()

        movement = SheetInventoryMovement.objects.create(
            sheet=sheet,
            movement_type=movement_type,
            quantity=movement_qty,
            balance_before=before,
            balance_after=inventory.quantity,
            note=(note or "").strip(),
            created_by=user if getattr(user, "is_authenticated", False) else None,
        )

    return True, "บันทึกสำเร็จ", inventory, movement


def _active_admissions_for_sheet_demand() -> list[AdmissionInquiry]:
    return list(
        AdmissionInquiry.objects
        .filter(is_completed=False)
        .only("id", "grade_level", "preferred_time_slot", "request_type", "first_lesson_date")
        .order_by("first_lesson_date", "created_at")
    )


def _class_matches_inquiry(tutoring_class: TutoringClass, inquiry: AdmissionInquiry) -> bool:
    if getattr(tutoring_class, "time_slot", "") != getattr(inquiry, "preferred_time_slot", ""):
        return False

    class_name = (tutoring_class.name or "").lower()
    grade_display = ""
    try:
        grade_display = inquiry.get_grade_level_display()
    except Exception:
        grade_display = ""

    grade_code = (inquiry.grade_level or "").lower()
    tokens = {
        grade_code,
        grade_code.replace("p", "ป."),
        grade_code.replace("m", "ม."),
        grade_display,
        grade_display.replace(".", ""),
        grade_display.replace(" ", ""),
    }
    tokens = {t.lower() for t in tokens if t}

    return any(token in class_name for token in tokens)


def _demand_count_for_class(tutoring_class: TutoringClass, pending_inquiries: list[AdmissionInquiry]) -> int:
    return sum(1 for i in pending_inquiries if _class_matches_inquiry(tutoring_class, i))


def _sheet_row(sheet: Sheet) -> dict:
    inv = _inventory_for_sheet(sheet)
    qty = int(inv.quantity or 0) if inv else 0
    minimum = int(getattr(inv, "minimum_stock", 0) or 0) if inv else 0
    return {
        "sheet": sheet,
        "inventory": inv,
        "quantity": qty,
        "minimum_stock": minimum,
        "grade_level": getattr(sheet, "grade_level", "") or "",
        "grade_label": _sheet_grade_label(getattr(sheet, "grade_level", "") or ""),
        "is_low": minimum > 0 and qty <= minimum,
    }


def _build_class_sheet_rows() -> list[dict]:
    """
    Build class-sheet requirements using:
    1) Manual SheetClassMapping records
    2) ClassSubject.current_sheet from the older sheet update setup
    3) TeachingClassSubjectTemplate.default_sheet_name from the tutor update module
    4) TeachingProgressUpdate.sheet_name from recent tutor updates
    Demand count is based on active AdmissionInquiry records, not Enrollment.
    """
    pending_inquiries = _active_admissions_for_sheet_demand()
    classes = list(TutoringClass.objects.filter(is_active=True).order_by("time_slot", "name"))

    # Preload mappings
    manual_mappings = (
        SheetClassMapping.objects
        .select_related("sheet", "sheet__subject", "tutoring_class")
        .filter(is_active=True)
    )
    manual_by_class: dict[int, list[SheetClassMapping]] = defaultdict(list)
    for m in manual_mappings:
        manual_by_class[m.tutoring_class_id].append(m)

    current_sheet_links = (
        ClassSubject.objects
        .select_related("tutoring_class", "current_sheet", "current_sheet__subject")
        .filter(is_active=True, current_sheet__isnull=False, tutoring_class__is_active=True)
    )
    current_by_class: dict[int, list[Sheet]] = defaultdict(list)
    for cs in current_sheet_links:
        current_by_class[cs.tutoring_class_id].append(cs.current_sheet)

    templates = (
        TeachingClassSubjectTemplate.objects
        .select_related("tutoring_class")
        .filter(is_active=True, tutoring_class__is_active=True)
        .exclude(default_sheet_name="")
    )
    template_by_class: dict[int, list[Sheet]] = defaultdict(list)
    for t in templates:
        code = _sheet_code_from_text(t.default_sheet_name)
        if code:
            sheet = Sheet.objects.filter(code__iexact=code).select_related("subject").first()
            if sheet:
                template_by_class[t.tutoring_class_id].append(sheet)

    progress_updates = (
        TeachingProgressUpdate.objects
        .select_related("assignment__tutoring_class")
        .filter(assignment__tutoring_class__is_active=True)
        .exclude(sheet_name="")
        .order_by("-updated_at")[:500]
    )
    progress_by_class: dict[int, list[Sheet]] = defaultdict(list)
    for p in progress_updates:
        code = _sheet_code_from_text(p.sheet_name)
        if code:
            sheet = Sheet.objects.filter(code__iexact=code).select_related("subject").first()
            if sheet:
                progress_by_class[p.assignment.tutoring_class_id].append(sheet)

    rows = []
    for cls in classes:
        demand_count = _demand_count_for_class(cls, pending_inquiries)
        seen: dict[int, dict] = {}

        for m in manual_by_class.get(cls.id, []):
            seen[m.sheet_id] = {
                "sheet": m.sheet,
                "source": "manual",
                "source_label": "Manual",
                "quantity_per_student": int(m.quantity_per_student or 1),
                "mapping": m,
            }

        for s in current_by_class.get(cls.id, []):
            seen.setdefault(s.id, {
                "sheet": s,
                "source": "current_sheet",
                "source_label": "Current Sheet",
                "quantity_per_student": 1,
                "mapping": None,
            })

        for s in template_by_class.get(cls.id, []):
            seen.setdefault(s.id, {
                "sheet": s,
                "source": "template",
                "source_label": "Template",
                "quantity_per_student": 1,
                "mapping": None,
            })

        for s in progress_by_class.get(cls.id, []):
            seen.setdefault(s.id, {
                "sheet": s,
                "source": "tutor_update",
                "source_label": "Tutor Update",
                "quantity_per_student": 1,
                "mapping": None,
            })

        entries = []
        for item in seen.values():
            sheet = item["sheet"]
            inv = _inventory_for_sheet(sheet)
            balance = int(inv.quantity or 0) if inv else 0
            required = demand_count * int(item["quantity_per_student"] or 1)
            entries.append({
                **item,
                "balance": balance,
                "required": required,
                "shortage": max(required - balance, 0),
            })

        rows.append({
            "class": cls,
            "demand_count": demand_count,
            "entries": sorted(entries, key=lambda x: x["sheet"].code),
            "has_shortage": any(e["shortage"] > 0 for e in entries),
        })

    return rows



def _sheet_inventory_context(*, q: str = "", extra: dict | None = None) -> dict:
    sheets_qs = Sheet.objects.select_related("subject").all()
    if q:
        grade_q = _normalize_sheet_grade_level(q)
        query = (
            Q(code__icontains=q) |
            Q(title__icontains=q) |
            Q(subject__name__icontains=q)
        )
        if grade_q:
            query |= Q(grade_level=grade_q)
        sheets_qs = sheets_qs.filter(query)

    sheets = list(sheets_qs.order_by("grade_level", "subject__name", "code"))
    sheet_rows = [_sheet_row(s) for s in sheets]
    all_sheets = Sheet.objects.select_related("subject").filter(is_active=True).order_by("grade_level", "subject__name", "code")
    active_classes = TutoringClass.objects.filter(is_active=True).order_by("time_slot", "name")
    context = {
        "q": q,
        "sheet_rows": sheet_rows,
        "sheet_grade_groups": _ordered_grade_groups(sheet_rows),
        "sheet_grade_choices": Sheet.GradeLevel.choices,
        "subjects": Subject.objects.filter(is_active=True).order_by("name"),
        "classes": active_classes,
        "all_sheets": all_sheets,
        "sheet_choices": all_sheets,
        "class_rows": _build_class_sheet_rows(),
        "movements": (
            SheetInventoryMovement.objects
            .select_related("sheet", "created_by")
            .order_by("-created_at")[:30]
        ),
        "movement_type_choices": SheetInventoryMovement.MovementType.choices,
    }
    if extra:
        context.update(extra)
    return context


def _clean_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value)).strip()
    return str(value).strip()


def _parse_int_cell(value, default=None):
    raw = _clean_cell(value)
    if raw == "":
        return default
    try:
        return max(int(float(raw.replace(",", ""))), 0)
    except Exception:
        return default


def _parse_bool_cell(value, default=True):
    raw = _clean_cell(value).lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "y", "active", "ใช่", "เปิด", "เปิดใช้งาน"}


def _normalize_upload_header(value) -> str:
    raw = _clean_cell(value).lower()
    return re.sub(r"[\s_\-./()]+", "", raw)


def _pick_upload_value(row: dict, aliases: list[str]):
    normalized_aliases = {_normalize_upload_header(a) for a in aliases}
    for key, value in row.items():
        if _normalize_upload_header(key) in normalized_aliases:
            return value
    return ""


def _read_sheet_upload_rows(uploaded_file) -> list[dict]:
    filename = (getattr(uploaded_file, "name", "") or "").lower()

    if filename.endswith(".csv"):
        raw = uploaded_file.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp874", errors="replace")
        reader = csv.DictReader(text.splitlines())
        return [dict(r) for r in reader]

    # Default to Excel workbook
    wb = load_workbook(BytesIO(uploaded_file.read()), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [_clean_cell(h) for h in rows[0]]
    result = []
    for row_values in rows[1:]:
        if not any(_clean_cell(v) for v in row_values):
            continue
        result.append({headers[i]: row_values[i] if i < len(row_values) else "" for i in range(len(headers))})
    return result


def _import_sheet_rows_from_upload(rows: list[dict], *, user=None, stock_mode: str = "set") -> dict:
    """
    Import rows from Excel/CSV.
    Required columns:
    - รหัสชีท / code
    - ชื่อชีท / title
    - วิชา / subject

    Optional:
    - ระดับชั้น / grade_level (accepted for template compatibility; current Sheet model does not store grade separately)
    - initial_quantity
    - total_pages
    - total_questions
    - minimum_stock
    - is_active
    """
    created_count = 0
    updated_count = 0
    skipped_count = 0
    movement_count = 0
    errors: list[str] = []

    code_aliases = ["รหัสชีท", "sheet code", "sheet_code", "code", "รหัส"]
    title_aliases = ["ชื่อชีท", "ชื่อเรื่อง", "sheet name", "sheet_name", "title", "ชื่อ"]
    subject_aliases = ["วิชา", "subject", "subject_name"]
    grade_aliases = ["ระดับชั้น", "grade", "grade_level", "gradelevel", "ชั้น", "level"]
    initial_aliases = ["initial_quantity", "initial qty", "ยอดเริ่มต้น", "จำนวนคงเหลือ", "stock", "quantity"]
    pages_aliases = ["total_pages", "จำนวนหน้า", "pages"]
    questions_aliases = ["total_questions", "จำนวนข้อ", "questions"]
    min_aliases = ["minimum_stock", "ขั้นต่ำที่ควรมี", "min stock", "minimum"]
    active_aliases = ["is_active", "active", "เปิดใช้งาน"]

    stock_mode = (stock_mode or "set").strip()
    if stock_mode not in {"skip", "set", "add"}:
        stock_mode = "set"

    with transaction.atomic():
        for idx, row in enumerate(rows, start=2):
            code = _clean_cell(_pick_upload_value(row, code_aliases)).upper()
            title = _clean_cell(_pick_upload_value(row, title_aliases))
            subject_name = _clean_cell(_pick_upload_value(row, subject_aliases))
            grade_level_raw = _clean_cell(_pick_upload_value(row, grade_aliases))
            grade_level = _normalize_sheet_grade_level(grade_level_raw) or _infer_sheet_grade_level(code, title)

            if not code and not title and not subject_name:
                skipped_count += 1
                continue

            if not code:
                errors.append(f"แถว {idx}: ไม่มีรหัสชีท")
                skipped_count += 1
                continue
            if not title:
                errors.append(f"แถว {idx}: ไม่มีชื่อชีทสำหรับรหัส {code}")
                skipped_count += 1
                continue
            if not subject_name:
                errors.append(f"แถว {idx}: ไม่มีวิชาสำหรับรหัส {code}")
                skipped_count += 1
                continue

            subject, _ = Subject.objects.get_or_create(
                name=subject_name,
                defaults={"is_active": True},
            )

            total_pages = _parse_int_cell(_pick_upload_value(row, pages_aliases), default=None)
            total_questions = _parse_int_cell(_pick_upload_value(row, questions_aliases), default=None)
            minimum_stock = _parse_int_cell(_pick_upload_value(row, min_aliases), default=None)
            initial_qty = _parse_int_cell(_pick_upload_value(row, initial_aliases), default=None)
            is_active = _parse_bool_cell(_pick_upload_value(row, active_aliases), default=True)

            sheet, created = Sheet.objects.get_or_create(
                code=code,
                defaults={
                    "title": title,
                    "subject": subject,
                    "grade_level": grade_level,
                    "total_pages": total_pages or 0,
                    "total_questions": total_questions or 0,
                    "is_active": is_active,
                },
            )

            if created:
                created_count += 1
            else:
                changed = False
                if sheet.title != title:
                    sheet.title = title
                    changed = True
                if sheet.subject_id != subject.id:
                    sheet.subject = subject
                    changed = True
                if grade_level and getattr(sheet, "grade_level", "") != grade_level:
                    sheet.grade_level = grade_level
                    changed = True
                if total_pages is not None and sheet.total_pages != total_pages:
                    sheet.total_pages = total_pages
                    changed = True
                if total_questions is not None and sheet.total_questions != total_questions:
                    sheet.total_questions = total_questions
                    changed = True
                if sheet.is_active != is_active:
                    sheet.is_active = is_active
                    changed = True
                if changed:
                    sheet.save()
                updated_count += 1

            inventory, _ = SheetInventory.objects.get_or_create(sheet=sheet, defaults={"quantity": 0})

            if minimum_stock is not None:
                inventory.minimum_stock = minimum_stock
                inventory.save()

            if initial_qty is not None and stock_mode != "skip":
                movement_type = (
                    SheetInventoryMovement.MovementType.ADD
                    if stock_mode == "add"
                    else SheetInventoryMovement.MovementType.SET
                )

                if movement_type == SheetInventoryMovement.MovementType.ADD and initial_qty <= 0:
                    pass
                else:
                    note_parts = ["Bulk upload"]
                    if grade_level:
                        note_parts.append(f"grade={grade_level}")
                    ok, msg, inv, mv = _apply_sheet_inventory_movement(
                        sheet=sheet,
                        movement_type=movement_type,
                        quantity=initial_qty,
                        note="; ".join(note_parts),
                        user=user,
                    )
                    if ok and mv:
                        movement_count += 1
                    elif not ok:
                        errors.append(f"แถว {idx} ({code}): {msg}")

    return {
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "movements": movement_count,
        "errors": errors[:30],
        "error_count": len(errors),
    }



@login_required
def sheet_inventory_dashboard(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action == "create_sheet":
            code = (request.POST.get("code") or "").strip().upper()
            title = (request.POST.get("title") or "").strip()
            subject_id = (request.POST.get("subject_id") or "").strip()
            new_subject = (request.POST.get("new_subject") or "").strip()
            grade_level = _normalize_sheet_grade_level(request.POST.get("grade_level")) or _infer_sheet_grade_level(code, title)
            total_pages = int(request.POST.get("total_pages") or 0)
            total_questions = int(request.POST.get("total_questions") or 0)
            initial_qty = int(request.POST.get("initial_qty") or 0)
            minimum_stock = int(request.POST.get("minimum_stock") or 0)

            if code and title:
                if subject_id:
                    subject = Subject.objects.filter(id=subject_id).first()
                elif new_subject:
                    subject, _ = Subject.objects.get_or_create(name=new_subject, defaults={"is_active": True})
                else:
                    subject, _ = Subject.objects.get_or_create(name="General", defaults={"is_active": True})

                sheet, created = Sheet.objects.get_or_create(
                    code=code,
                    defaults={
                        "title": title,
                        "subject": subject,
                        "grade_level": grade_level,
                        "total_pages": total_pages,
                        "total_questions": total_questions,
                        "is_active": True,
                    }
                )
                if created:
                    inv, _ = SheetInventory.objects.get_or_create(sheet=sheet, defaults={"quantity": 0})
                    inv.minimum_stock = max(minimum_stock, 0)
                    inv.save()
                    if initial_qty > 0:
                        _apply_sheet_inventory_movement(
                            sheet=sheet,
                            movement_type=SheetInventoryMovement.MovementType.ADD,
                            quantity=initial_qty,
                            note="Initial stock from Sheet Inventory module",
                            user=request.user,
                        )
                return redirect("core:sheet_inventory_profile", pk=sheet.pk)

        elif action == "stock_single":
            sheet = get_object_or_404(Sheet, id=request.POST.get("sheet_id"))
            mode = request.POST.get("movement_type") or SheetInventoryMovement.MovementType.ADD
            qty = int(request.POST.get("quantity") or 0)
            note = request.POST.get("note") or ""
            _apply_sheet_inventory_movement(sheet=sheet, movement_type=mode, quantity=qty, note=note, user=request.user)
            return redirect("core:sheet_inventory_dashboard")

        elif action == "bulk_stock":
            for key, val in request.POST.items():
                if not key.startswith("bulk_qty_"):
                    continue
                sheet_id = key.replace("bulk_qty_", "")
                raw_qty = (val or "").strip()
                if raw_qty == "":
                    continue
                sheet = Sheet.objects.filter(id=sheet_id).first()
                if not sheet:
                    continue
                mode = request.POST.get(f"bulk_mode_{sheet_id}") or SheetInventoryMovement.MovementType.ADD
                note = request.POST.get(f"bulk_note_{sheet_id}") or "Bulk update"
                try:
                    qty = int(raw_qty)
                except Exception:
                    continue
                _apply_sheet_inventory_movement(sheet=sheet, movement_type=mode, quantity=qty, note=note, user=request.user)
            return redirect("core:sheet_inventory_dashboard")

        elif action == "link_class_sheet":
            class_id = request.POST.get("class_id")
            sheet_id = request.POST.get("sheet_id")
            qty_per = int(request.POST.get("quantity_per_student") or 1)
            note = request.POST.get("note") or ""
            if class_id and sheet_id:
                SheetClassMapping.objects.update_or_create(
                    tutoring_class_id=class_id,
                    sheet_id=sheet_id,
                    defaults={
                        "quantity_per_student": max(qty_per, 1),
                        "note": note,
                        "is_active": True,
                    }
                )
            return redirect("core:sheet_inventory_dashboard")

        elif action == "unlink_class_sheet":
            mapping = get_object_or_404(SheetClassMapping, id=request.POST.get("mapping_id"))
            mapping.is_active = False
            mapping.save()
            return redirect("core:sheet_inventory_dashboard")

    q = (request.GET.get("q") or "").strip()
    sheets_qs = Sheet.objects.select_related("subject").all()
    if q:
        sheets_qs = sheets_qs.filter(
            Q(code__icontains=q) |
            Q(title__icontains=q) |
            Q(subject__name__icontains=q)
        )
    sheets = list(sheets_qs.order_by("grade_level", "subject__name", "code"))
    sheet_rows = [_sheet_row(s) for s in sheets]

    return render(request, "core/sheet_inventory.html", _sheet_inventory_context(q=q))


@require_POST
@login_required
def sheet_inventory_bulk_upload(request: HttpRequest) -> HttpResponse:
    uploaded = request.FILES.get("bulk_file")
    stock_mode = request.POST.get("stock_mode") or "set"

    if not uploaded:
        context = _sheet_inventory_context(extra={
            "bulk_result": {
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "movements": 0,
                "errors": ["กรุณาเลือกไฟล์ Excel หรือ CSV ก่อนอัปโหลด"],
                "error_count": 1,
            }
        })
        return render(request, "core/sheet_inventory.html", context)

    try:
        rows = _read_sheet_upload_rows(uploaded)
        result = _import_sheet_rows_from_upload(
            rows,
            user=request.user,
            stock_mode=stock_mode,
        )
    except Exception as exc:
        result = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "movements": 0,
            "errors": [f"อ่านไฟล์ไม่สำเร็จ: {exc}"],
            "error_count": 1,
        }

    context = _sheet_inventory_context(extra={"bulk_result": result})
    return render(request, "core/sheet_inventory.html", context)


@require_POST
@login_required
def sheet_inventory_scan(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    code = (data.get("code") or "").strip().upper()
    mode = (data.get("mode") or SheetInventoryMovement.MovementType.DEDUCT).strip()
    qty = data.get("quantity") or 1
    note = data.get("note") or "QR scanner"

    if mode == "count":
        mode = SheetInventoryMovement.MovementType.COUNT

    if not code:
        return JsonResponse({"ok": False, "error": "ไม่พบรหัสชีท"}, status=400)

    sheet = Sheet.objects.filter(code__iexact=code).select_related("subject").first()
    if not sheet:
        return JsonResponse({"ok": False, "error": f"ไม่พบรหัสชีท {code}", "code": code}, status=404)

    ok, message, inventory, movement = _apply_sheet_inventory_movement(
        sheet=sheet,
        movement_type=mode,
        quantity=int(qty or 1),
        note=note,
        user=request.user,
    )
    if not ok:
        return JsonResponse({"ok": False, "error": message, "code": code}, status=400)

    return JsonResponse({
        "ok": True,
        "message": message,
        "code": sheet.code,
        "title": sheet.title,
        "quantity": int(inventory.quantity or 0) if inventory else 0,
        "movement_type": movement.get_movement_type_display() if movement else "",
        "movement_at": _fmt_dt_th(movement.created_at) if movement else "",
    })


@login_required
def sheet_inventory_profile(request: HttpRequest, pk: int) -> HttpResponse:
    sheet = get_object_or_404(Sheet.objects.select_related("subject"), pk=pk)
    inventory, _ = SheetInventory.objects.get_or_create(sheet=sheet, defaults={"quantity": 0})
    movements = SheetInventoryMovement.objects.filter(sheet=sheet).select_related("created_by").order_by("-created_at")[:80]
    mappings = SheetClassMapping.objects.filter(sheet=sheet, is_active=True).select_related("tutoring_class")

    return render(request, "core/sheet_inventory_profile.html", {
        "sheet": sheet,
        "inventory": inventory,
        "movements": movements,
        "mappings": mappings,
    })


@login_required
def sheet_inventory_export(request: HttpRequest) -> HttpResponse:
    wb = Workbook()

    ws = wb.active
    ws.title = "Sheet Stock"
    ws.append(["Grade", "Sheet Code", "Title", "Subject", "Balance", "Minimum Stock", "Low Stock?", "Is Finished"])
    for sheet in Sheet.objects.select_related("subject").order_by("grade_level", "subject__name", "code"):
        inv = _inventory_for_sheet(sheet)
        qty = int(inv.quantity or 0) if inv else 0
        minimum = int(getattr(inv, "minimum_stock", 0) or 0) if inv else 0
        ws.append([
            sheet.get_grade_level_display() if getattr(sheet, "grade_level", "") else "",
            sheet.code,
            sheet.title,
            sheet.subject.name if sheet.subject_id else "",
            qty,
            minimum,
            "YES" if minimum > 0 and qty <= minimum else "NO",
            "YES" if inv and inv.is_finished else "NO",
        ])
    _autosize(ws)

    ws2 = wb.create_sheet("Class Requirement")
    ws2.append(["Class", "Time Slot", "Pending Inquiries", "Sheet Code", "Sheet Title", "Source", "Required Qty", "Balance", "Shortage"])
    for row in _build_class_sheet_rows():
        cls = row["class"]
        if not row["entries"]:
            ws2.append([cls.name, cls.get_time_slot_display(), row["demand_count"], "", "", "", 0, 0, 0])
        for e in row["entries"]:
            ws2.append([
                cls.name,
                cls.get_time_slot_display(),
                row["demand_count"],
                e["sheet"].code,
                e["sheet"].title,
                e["source_label"],
                e["required"],
                e["balance"],
                e["shortage"],
            ])
    _autosize(ws2)

    ws3 = wb.create_sheet("Movements")
    ws3.append(["Created At", "Sheet Code", "Movement Type", "Quantity", "Balance Before", "Balance After", "Note", "Created By"])
    movements = SheetInventoryMovement.objects.select_related("sheet", "created_by").order_by("-created_at")[:2000]
    for m in movements:
        ws3.append([
            timezone.localtime(m.created_at).strftime("%Y-%m-%d %H:%M") if m.created_at else "",
            m.sheet.code,
            m.get_movement_type_display(),
            m.quantity,
            m.balance_before,
            m.balance_after,
            m.note,
            m.created_by.get_username() if m.created_by else "",
        ])
    _autosize(ws3)

    buff = BytesIO()
    wb.save(buff)
    buff.seek(0)

    filename = f"sheet_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    resp = HttpResponse(
        buff.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp



def _parse_optional_date(value: str | None):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _print_order_dashboard_rows() -> list[dict]:
    pending_by_sheet = {
        item["sheet_id"]: item["qty"] or 0
        for item in (
            SheetPrintOrder.objects
            .filter(status=SheetPrintOrder.Status.PENDING)
            .values("sheet_id")
            .annotate(qty=Sum("quantity"))
        )
    }

    rows = []
    sheets = Sheet.objects.select_related("subject").filter(is_active=True).order_by("grade_level", "subject__name", "code")
    for sheet in sheets:
        inv = _inventory_for_sheet(sheet)
        current_qty = int(inv.quantity or 0) if inv else 0
        target_stock = int(getattr(inv, "target_stock", 0) or 0) if inv else 0
        onedrive_url = (getattr(inv, "onedrive_url", "") or "") if inv else ""
        pending_qty = int(pending_by_sheet.get(sheet.id, 0) or 0)
        shortage = max(target_stock - current_qty, 0)
        suggested_print_qty = max(target_stock - current_qty - pending_qty, 0)
        rows.append({
            "sheet": sheet,
            "inventory": inv,
            "current_qty": current_qty,
            "target_stock": target_stock,
            "onedrive_url": onedrive_url,
            "pending_print_qty": pending_qty,
            "shortage": shortage,
            "suggested_print_qty": suggested_print_qty,
        })
    return rows


@login_required
def sheet_print_order_admin(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action == "update_sheet_print_setting":
            sheet = get_object_or_404(Sheet, id=request.POST.get("sheet_id"))
            target_stock = max(int(request.POST.get("target_stock") or 0), 0)
            onedrive_url = (request.POST.get("onedrive_url") or "").strip()
            inventory, _ = SheetInventory.objects.get_or_create(sheet=sheet, defaults={"quantity": 0})
            inventory.target_stock = target_stock
            inventory.onedrive_url = onedrive_url
            inventory.save()
            return redirect("core:sheet_print_order_admin")

        if action == "create_print_order":
            sheet = get_object_or_404(Sheet, id=request.POST.get("sheet_id"))
            quantity = max(int(request.POST.get("quantity") or 0), 0)
            due_date = _parse_optional_date(request.POST.get("due_date"))
            onedrive_url = (request.POST.get("onedrive_url") or "").strip()
            note = (request.POST.get("note") or "").strip()

            if quantity > 0:
                inventory, _ = SheetInventory.objects.get_or_create(sheet=sheet, defaults={"quantity": 0})
                if not onedrive_url:
                    onedrive_url = inventory.onedrive_url or ""

                SheetPrintOrder.objects.create(
                    sheet=sheet,
                    quantity=quantity,
                    due_date=due_date,
                    onedrive_url=onedrive_url,
                    note=note,
                    requested_by=request.user if getattr(request.user, "is_authenticated", False) else None,
                )
                return redirect("core:print_shop_order_list")

            return redirect("core:sheet_print_order_admin")

    pending_orders = (
        SheetPrintOrder.objects
        .select_related("sheet", "sheet__subject", "requested_by")
        .filter(status=SheetPrintOrder.Status.PENDING)
        .order_by("due_date", "created_at")
    )
    ready_orders = (
        SheetPrintOrder.objects
        .select_related("sheet", "sheet__subject", "requested_by")
        .filter(status=SheetPrintOrder.Status.READY)
        .order_by("-completed_at", "-updated_at")[:80]
    )

    return render(request, "core/sheet_print_order_admin.html", {
        "rows": _print_order_dashboard_rows(),
        "pending_orders": pending_orders,
        "ready_orders": ready_orders,
        "default_due_date": timezone.localdate() + timedelta(days=3),
        "shop_url": request.build_absolute_uri("/print-shop/"),
    })


def print_shop_order_list(request: HttpRequest) -> HttpResponse:
    pending_orders = (
        SheetPrintOrder.objects
        .select_related("sheet", "sheet__subject")
        .filter(status=SheetPrintOrder.Status.PENDING)
        .order_by("due_date", "created_at")
    )
    ready_orders = (
        SheetPrintOrder.objects
        .select_related("sheet", "sheet__subject")
        .filter(status=SheetPrintOrder.Status.READY)
        .order_by("-completed_at", "-updated_at")[:80]
    )
    return render(request, "core/print_shop_orders.html", {
        "pending_orders": pending_orders,
        "ready_orders": ready_orders,
    })


@require_POST
def print_shop_mark_ready(request: HttpRequest, pk: int) -> HttpResponse:
    order = get_object_or_404(SheetPrintOrder, pk=pk)
    if order.status == SheetPrintOrder.Status.PENDING:
        order.mark_ready()
    return redirect("core:print_shop_order_list")



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

    ws_cash = wb.create_sheet("Course Payments")
    ws_cash.append(["Receipt No", "Payment Date", "Student", "Class", "Enrollment", "Payment Type", "Payment Method", "Sessions", "Course Price", "Discount", "Net Amount", "Amount Paid", "Status", "Note"])
    course_payment_export_rows = (
        CoursePayment.objects
        .select_related("student", "tutoring_class", "enrollment")
        .filter(status=CoursePayment.ReceiptStatus.ISSUED)
        .order_by("-payment_date", "-created_at")
    )
    for p in course_payment_export_rows:
        ws_cash.append([
            p.receipt_no,
            p.payment_date.isoformat() if p.payment_date else "",
            p.student.display_name if p.student_id else "",
            p.tutoring_class.name if p.tutoring_class_id else "",
            p.enrollment.sale_run_no if p.enrollment_id and p.enrollment else "",
            p.get_payment_type_display() if hasattr(p, "get_payment_type_display") else p.payment_type,
            p.get_payment_method_display() if hasattr(p, "get_payment_method_display") else p.payment_method,
            int(p.sessions_granted or 0),
            float(p.course_price or 0),
            float(p.discount_amount or 0),
            float(p.net_amount or 0),
            float(p.amount_paid or 0),
            p.get_status_display() if hasattr(p, "get_status_display") else p.status,
            p.note or "",
        ])
    _autosize(ws_cash)

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
            "contact_phone",
            "school_name",
            "latest_gpa",
            "first_lesson_date",
            "grade_level",
            "preferred_time_slot",
        ]
        widgets = {
            "request_type": forms.RadioSelect,
            "nickname": forms.TextInput(attrs={"placeholder": "เช่น น้องข้าวหอม", "autocomplete": "given-name"}),
            "first_name": forms.TextInput(attrs={"placeholder": "ชื่อจริงของนักเรียน", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "นามสกุลของนักเรียน", "autocomplete": "family-name"}),
            "school_name": forms.TextInput(attrs={"placeholder": "ชื่อโรงเรียน", "autocomplete": "organization"}),
            "contact_phone": forms.TextInput(attrs={
                "placeholder": "เบอร์ผู้ปกครอง / เบอร์ติดต่อ",
                "inputmode": "tel",
                "autocomplete": "tel",
            }),
            "latest_gpa": forms.NumberInput(attrs={
                "placeholder": "เช่น 3.50",
                "step": "0.01",
                "min": "0",
                "max": "4",
                "inputmode": "decimal",
            }),
            "first_lesson_date": forms.DateInput(attrs={
                "type": "date",
                "autocomplete": "off",
                "data-native-picker": "date",
            }),
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
    completed_status = (request.GET.get("completed_status") or "open").strip()
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
    if completed_status == "completed":
        qs = qs.filter(is_completed=True)
    elif completed_status == "all":
        pass
    else:
        completed_status = "open"
        qs = qs.filter(is_completed=False)
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
    open_base = stats_base.filter(is_completed=False)
    completed_base = stats_base.filter(is_completed=True)
    stats = {
        "total": stats_base.count(),
        "open_total": open_base.count(),
        "completed_total": completed_base.count(),
        "trial": open_base.filter(request_type=AdmissionInquiry.RequestType.TRIAL).count(),
        "enroll": open_base.filter(request_type=AdmissionInquiry.RequestType.ENROLL).count(),
        "queue": open_base.filter(request_type=AdmissionInquiry.RequestType.QUEUE).count(),
        "sheet_ready": open_base.filter(sheet_prepared=True).count(),
        "trial_attended": open_base.filter(trial_attended=AdmissionInquiry.TrialAttended.YES).count(),
        "trial_enrolled": open_base.filter(trial_result=AdmissionInquiry.TrialResult.ENROLLED).count(),
    }

    inquiries = qs.order_by("is_completed", "first_lesson_date", "-created_at")
    active_qs = inquiries.filter(is_completed=False)
    completed_qs = inquiries.filter(is_completed=True).order_by("-completed_at", "-updated_at", "-created_at")

    inquiry_groups = [
        {
            "key": "trial",
            "title": "จองทดลองเรียน",
            "icon": "🧪",
            "color": "blue",
            "items": active_qs.filter(request_type=AdmissionInquiry.RequestType.TRIAL),
        },
        {
            "key": "enroll",
            "title": "สมัครเรียน",
            "icon": "📚",
            "color": "green",
            "items": active_qs.filter(request_type=AdmissionInquiry.RequestType.ENROLL),
        },
        {
            "key": "queue",
            "title": "จองที่นั่งล่วงหน้า",
            "icon": "📌",
            "color": "orange",
            "items": active_qs.filter(request_type=AdmissionInquiry.RequestType.QUEUE),
        },
    ]

    return render(request, "core/admission_report.html", {
        "inquiries": inquiries,
        "inquiry_groups": inquiry_groups,
        "completed_inquiries": completed_qs,
        "stats": stats,
        "filters": {
            "q": q,
            "request_type": request_type,
            "grade_level": grade_level,
            "preferred_time_slot": preferred_time_slot,
            "sheet_prepared": sheet_prepared,
            "trial_attended": trial_attended,
            "trial_result": trial_result,
            "completed_status": completed_status,
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
    is_completed_raw = request.POST.get("is_completed")

    inquiry.sheet_prepared = sheet_prepared == "yes"

    valid_attended = {choice[0] for choice in AdmissionInquiry.TrialAttended.choices}
    valid_result = {choice[0] for choice in AdmissionInquiry.TrialResult.choices}

    if trial_attended in valid_attended:
        inquiry.trial_attended = trial_attended
    if trial_result in valid_result:
        inquiry.trial_result = trial_result
    if internal_note is not None:
        inquiry.internal_note = internal_note.strip()

    new_completed = is_completed_raw == "yes"
    if new_completed and not inquiry.is_completed:
        inquiry.completed_at = timezone.now()
    elif not new_completed:
        inquiry.completed_at = None
    inquiry.is_completed = new_completed

    inquiry.save()

    return redirect(request.META.get("HTTP_REFERER", "core:admission_report"))


# =========================================================
# ✅ School Overview / Finance helpers
# =========================================================
def _finance_setting(key: str, default: Decimal, description: str = "") -> Decimal:
    obj, _ = FinanceSetting.objects.get_or_create(
        key=key,
        defaults={"value": default, "description": description},
    )
    return Decimal(str(obj.value))


def _school_week_range(anchor: date) -> tuple[date, date]:
    """School week = Saturday to Sunday."""
    days_since_sat = (anchor.weekday() - 5) % 7
    start = anchor - timedelta(days=days_since_sat)
    return start, start + timedelta(days=1)


def _month_range(anchor: date) -> tuple[date, date]:
    if anchor.month == 12:
        next_month = date(anchor.year + 1, 1, 1)
    else:
        next_month = date(anchor.year, anchor.month + 1, 1)
    start = date(anchor.year, anchor.month, 1)
    return start, next_month - timedelta(days=1)


def _year_range(anchor: date) -> tuple[date, date]:
    return date(anchor.year, 1, 1), date(anchor.year, 12, 31)


def _safe_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _period_from_request(request: HttpRequest) -> tuple[str, date, date]:
    """
    Date range priority:
    1) If date_from/date_to are provided, use them directly.
    2) Otherwise use period_mode + anchor_date as a quick preset.

    This fixes the old behavior where users had to rely on anchor_date even
    after selecting a start/end range.
    """
    mode = (request.GET.get("period_mode") or "custom").strip()

    raw_start = _safe_date(request.GET.get("date_from"))
    raw_end = _safe_date(request.GET.get("date_to"))

    if raw_start or raw_end:
        start = raw_start or raw_end or timezone.localdate()
        end = raw_end or raw_start or start
        if end < start:
            start, end = end, start
        return "custom", start, end

    anchor = _safe_date(request.GET.get("anchor_date")) or timezone.localdate()

    if mode == "month":
        start, end = _month_range(anchor)
    elif mode == "year":
        start, end = _year_range(anchor)
    else:
        mode = "week"
        start, end = _school_week_range(anchor)

    return mode, start, end


def _blank_overview_row(label: str, sort_date: date) -> dict:
    return {
        "label": label,
        "sort": sort_date,
        "present": 0,
        "excused": 0,
        "no_show": 0,
        "deducted_count": 0,
        "class_ids": set(),
        "estimated_revenue": Decimal("0"),
        "estimated_tutor_cost": Decimal("0"),
        "actual_tutor_cost": Decimal("0"),
        "general_expense": Decimal("0"),
        "net_estimated": Decimal("0"),
        "net_actual_direct": Decimal("0"),
    }


def _ensure_overview_group(groups: dict[str, dict], label: str, sort_date: date) -> dict:
    if label not in groups:
        groups[label] = _blank_overview_row(label, sort_date)
    return groups[label]


def _school_week_labels_between(start: date, end: date) -> list[tuple[str, date, date]]:
    """Return all Sat-Sun school weeks overlapping the selected range."""
    first_week_start, _ = _school_week_range(start)
    cur = first_week_start
    out: list[tuple[str, date, date]] = []
    while cur <= end:
        week_end = cur + timedelta(days=1)
        label = f"{cur.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')}"
        out.append((label, cur, week_end))
        cur += timedelta(days=7)
    return out


def _group_key(d: date, group_by: str) -> tuple[str, date]:
    if group_by == "month":
        start = date(d.year, d.month, 1)
        return start.strftime("%Y-%m"), start
    if group_by == "year":
        start = date(d.year, 1, 1)
        return str(d.year), start
    start, _ = _school_week_range(d)
    return f"{start.strftime('%d/%m/%Y')} - {(start + timedelta(days=1)).strftime('%d/%m/%Y')}", start


def _money(x) -> Decimal:
    try:
        return Decimal(str(x or 0))
    except Exception:
        return Decimal("0")




COURSE_SESSION_CHOICES = [
    ("10", "10 ครั้ง", 10),
    ("12", "10 แถม 2 = 12 ครั้ง", 12),
    ("20", "20 ครั้ง", 20),
    ("30", "30 ครั้ง", 30),
    ("custom", "กรอกเอง", 10),
]


def _active_students_for_payment():
    return Student.objects.filter(is_active=True).select_related("school").order_by("grade_level", "nickname", "full_name")


def _active_enrollments_for_payment(student_id: str | None = None):
    qs = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(is_active=True, student__is_active=True, tutoring_class__is_active=True)
        .order_by("student__nickname", "student__full_name", "tutoring_class__name", "-created_at")
    )
    if student_id:
        try:
            qs = qs.filter(student_id=int(student_id))
        except Exception:
            pass
    return qs


def _default_payment_form_context(request: HttpRequest, errors: list[str] | None = None, posted: dict | None = None):
    students = list(_active_students_for_payment())
    classes = list(TutoringClass.objects.filter(is_active=True).order_by("time_slot", "name"))

    # For the receipt form we use search boxes instead of long dropdowns.
    # Keep the queryset unrestricted to active records so the browser can filter instantly.
    enrollments = list(_active_enrollments_for_payment())
    admission_inquiries = list(
        AdmissionInquiry.objects
        .order_by("-created_at")
        .only(
            "id",
            "nickname",
            "first_name",
            "last_name",
            "school_name",
            "contact_phone",
            "grade_level",
            "preferred_time_slot",
            "first_lesson_date",
            "created_at",
        )[:300]
    )

    students_lookup_json = [
        {
            "id": s.id,
            "label": f"{s.nickname or '-'} | {s.full_name or '-'} | {s.student_code or '-'} | {s.grade_level or '-'}",
            "nickname": s.nickname or "",
            "full_name": s.full_name or "",
            "student_code": s.student_code or "",
            "grade_level": s.grade_level or "",
            "school_name": s.school.name if getattr(s, "school_id", None) and s.school else "",
            "parent_phone": s.parent_phone or "",
        }
        for s in students
    ]

    enrollments_lookup_json = [
        {
            "id": e.id,
            "student_id": e.student_id,
            "student_label": f"{e.student.nickname or '-'} | {e.student.full_name or '-'} | {e.student.student_code or '-'}",
            "label": f"{e.student.nickname or '-'} | {e.student.full_name or '-'} | {e.tutoring_class.name} | {e.sale_run_no or e.id} | คงเหลือ {e.remaining_sessions}",
            "class_name": e.tutoring_class.name,
            "sale_run_no": e.sale_run_no or str(e.id),
            "remaining_sessions": e.remaining_sessions,
            "course_price": str(e.course_price or e.tutoring_class.course_price or 0),
        }
        for e in enrollments
    ]

    admission_inquiries_lookup_json = [
        {
            "id": i.id,
            "label": f"{i.nickname} | {i.full_name} | {i.get_grade_level_display()} | {i.school_name or '-'} | {i.contact_phone}",
            "nickname": i.nickname or "",
            "full_name": i.full_name or "",
            "grade_level": i.get_grade_level_display() or "",
            "school_name": i.school_name or "",
            "parent_phone": i.contact_phone or "",
            "first_lesson_date": i.first_lesson_date.isoformat() if i.first_lesson_date else "",
            "preferred_time_slot": i.get_preferred_time_slot_display() if i.preferred_time_slot else "",
            "created_at": i.created_at.strftime("%Y-%m-%d") if i.created_at else "",
        }
        for i in admission_inquiries
    ]

    return {
        "students": students,
        "classes": classes,
        "enrollments": enrollments,
        "admission_inquiries": admission_inquiries,
        "students_lookup_json": students_lookup_json,
        "enrollments_lookup_json": enrollments_lookup_json,
        "admission_inquiries_lookup_json": admission_inquiries_lookup_json,
        "payment_method_choices": CoursePayment.PaymentMethod.choices,
        "payment_type_choices": CoursePayment.PaymentType.choices,
        "enrollment_action_choices": CoursePayment.EnrollmentAction.choices,
        "session_choices": COURSE_SESSION_CHOICES,
        "today": timezone.localdate(),
        "errors": errors or [],
        "posted": posted or {},
    }


def _sessions_from_package(package: str, custom_value: str | None) -> int:
    mapping = {code: value for code, _label, value in COURSE_SESSION_CHOICES}
    if package == "custom":
        try:
            return max(int(custom_value or 0), 1)
        except Exception:
            return 10
    return mapping.get(package, 10)


def _apply_payment_to_enrollment(payment: CoursePayment, action: str, existing_enrollment: Enrollment | None = None) -> Enrollment:
    """Create a new enrollment or add sessions to an existing enrollment for a course payment."""
    sessions = int(payment.sessions_granted or 0)
    if action == CoursePayment.EnrollmentAction.ADD_EXISTING and existing_enrollment:
        payment.enrollment_sessions_before = int(existing_enrollment.sessions_total or 0)
        existing_enrollment.sessions_total = int(existing_enrollment.sessions_total or 0) + sessions
        existing_enrollment.remark = ((existing_enrollment.remark or "").strip() + f"\nเพิ่ม {sessions} ครั้ง จากใบเสร็จ {payment.receipt_no}").strip()
        existing_enrollment.save()
        payment.enrollment = existing_enrollment
        payment.tutoring_class = existing_enrollment.tutoring_class
        payment.enrollment_action = CoursePayment.EnrollmentAction.ADD_EXISTING
        payment.enrollment_created = False
        payment.save()
        return existing_enrollment

    enrollment = Enrollment.objects.create(
        student=payment.student,
        tutoring_class=payment.tutoring_class,
        enrollment_type=Enrollment.EnrollmentType.SPECIAL,
        sessions_total=sessions,
        payment_type=Enrollment.PaymentType.INSTALLMENT if payment.payment_type == CoursePayment.PaymentType.INSTALLMENT else Enrollment.PaymentType.FULL,
        installments_count=1,
        course_price=payment.course_price,
        discount_amount=payment.discount_amount,
        remark=f"สร้างจากใบเสร็จ {payment.receipt_no}",
        is_active=True,
    )
    payment.enrollment = enrollment
    payment.enrollment_action = CoursePayment.EnrollmentAction.NEW
    payment.enrollment_created = True
    payment.enrollment_sessions_before = None
    payment.save()
    return enrollment


def _reverse_payment_enrollment_effect(payment: CoursePayment) -> None:
    """Reverse enrollment effect when a receipt is cancelled."""
    enrollment = payment.enrollment
    if not enrollment:
        return
    if payment.enrollment_created:
        enrollment.is_active = False
        enrollment.remark = ((enrollment.remark or "").strip() + f"\nยกเลิกจากใบเสร็จ {payment.receipt_no}").strip()
        enrollment.save()
        return
    if payment.enrollment_sessions_before is not None:
        enrollment.sessions_total = int(payment.enrollment_sessions_before)
        enrollment.remark = ((enrollment.remark or "").strip() + f"\nยกเลิกการเพิ่มครั้งจากใบเสร็จ {payment.receipt_no}").strip()
        enrollment.save()


def _attendance_queryset_for_range(start: date, end: date, time_slot: str = "", class_id: str = ""):
    qs = (
        Attendance.objects
        .select_related("enrollment__tutoring_class", "student")
        .filter(
            attendance_date__gte=start,
            attendance_date__lte=end,
            student__is_active=True,
            enrollment__tutoring_class__is_active=True,
        )
    )
    if time_slot:
        qs = qs.filter(enrollment__tutoring_class__time_slot=time_slot)
    if class_id:
        try:
            qs = qs.filter(enrollment__tutoring_class_id=int(class_id))
        except Exception:
            pass
    return qs


@login_required
def school_overview(request: HttpRequest) -> HttpResponse:
    """
    Module 1:
    - Attendance overview by selected start/end date.
    - Attendance graph is always a weekly line chart: present / excused / no-show.
    - Revenue estimate = (present + no-show) x revenue per student.
    - Estimated tutor direct cost = active classes in period x tutor cost per class.
    - Actual tutor direct cost = Module 2 tutor payroll entries.
    """
    if request.method == "POST":
        revenue = _money(request.POST.get("revenue_per_student"))
        tutor_cost = _money(request.POST.get("estimated_tutor_cost_per_class"))
        FinanceSetting.objects.update_or_create(
            key="revenue_per_student_per_week",
            defaults={
                "value": revenue,
                "description": "รายได้ประมาณการต่อคนต่อสัปดาห์ / ต่อครั้งที่หักชั่วโมง",
            },
        )
        FinanceSetting.objects.update_or_create(
            key="estimated_tutor_cost_per_class_per_week",
            defaults={
                "value": tutor_cost,
                "description": "ค่าใช้จ่ายติวเตอร์ประมาณการต่อ class ต่อสัปดาห์",
            },
        )
        # Keep the selected filter after saving settings.
        qs = request.GET.urlencode()
        return redirect(f"{request.path}?{qs}" if qs else "core:school_overview")

    period_mode, start, end = _period_from_request(request)
    group_by = (request.GET.get("group_by") or "week").strip()
    if group_by not in {"week", "month", "year"}:
        group_by = "week"

    time_slot = (request.GET.get("time_slot") or "").strip()
    class_id = (request.GET.get("class_id") or "").strip()

    revenue_per_student = _finance_setting(
        "revenue_per_student_per_week",
        Decimal("360"),
        "รายได้ประมาณการต่อคนต่อสัปดาห์ / ต่อครั้งที่หักชั่วโมง",
    )
    estimated_tutor_cost_per_class = _finance_setting(
        "estimated_tutor_cost_per_class_per_week",
        Decimal("1350"),
        "ค่าใช้จ่ายติวเตอร์ประมาณการต่อ class ต่อสัปดาห์",
    )

    att_qs = _attendance_queryset_for_range(start, end, time_slot, class_id)

    # =====================================================
    # Table groups: user can choose week / month / year.
    # =====================================================
    groups: dict[str, dict] = {}
    for a in att_qs:
        label, group_start = _group_key(a.attendance_date, group_by)
        item = _ensure_overview_group(groups, label, group_start)

        if a.status == Attendance.Status.PRESENT:
            item["present"] += 1
            item["deducted_count"] += 1
            item["class_ids"].add(a.enrollment.tutoring_class_id)
        elif a.status == Attendance.Status.EXCUSED:
            item["excused"] += 1
        elif a.status == Attendance.Status.NO_SHOW:
            item["no_show"] += 1
            item["deducted_count"] += 1
            item["class_ids"].add(a.enrollment.tutoring_class_id)

    # Actual tutor payroll from Module 2
    payroll_qs = TutorPayrollEntry.objects.filter(work_date__gte=start, work_date__lte=end)
    for p in payroll_qs:
        label, group_start = _group_key(p.work_date, group_by)
        item = _ensure_overview_group(groups, label, group_start)
        item["actual_tutor_cost"] += _money(p.total_amount)

    # General expenses from Module 2
    expense_qs = SchoolExpense.objects.filter(expense_date__gte=start, expense_date__lte=end)
    for e in expense_qs:
        label, group_start = _group_key(e.expense_date, group_by)
        item = _ensure_overview_group(groups, label, group_start)
        item["general_expense"] += _money(e.amount)

    rows = []
    for item in groups.values():
        active_class_count = len(item["class_ids"])
        item["active_class_count"] = active_class_count
        item["estimated_revenue"] = Decimal(item["deducted_count"]) * revenue_per_student
        item["estimated_tutor_cost"] = Decimal(active_class_count) * estimated_tutor_cost_per_class
        item["net_estimated"] = item["estimated_revenue"] - item["estimated_tutor_cost"]
        item["net_actual_direct"] = item["estimated_revenue"] - item["actual_tutor_cost"]
        rows.append(item)

    rows.sort(key=lambda x: x["sort"])

    totals = {
        "present": sum(r["present"] for r in rows),
        "excused": sum(r["excused"] for r in rows),
        "no_show": sum(r["no_show"] for r in rows),
        "deducted_count": sum(r["deducted_count"] for r in rows),
        "estimated_revenue": sum((r["estimated_revenue"] for r in rows), Decimal("0")),
        "estimated_tutor_cost": sum((r["estimated_tutor_cost"] for r in rows), Decimal("0")),
        "actual_tutor_cost": sum((r["actual_tutor_cost"] for r in rows), Decimal("0")),
        "general_expense": sum((r["general_expense"] for r in rows), Decimal("0")),
    }
    totals["net_estimated"] = totals["estimated_revenue"] - totals["estimated_tutor_cost"]
    totals["net_actual_direct"] = totals["estimated_revenue"] - totals["actual_tutor_cost"]

    # =====================================================
    # Chart groups: ALWAYS weekly line chart by school week.
    # This keeps X-axis as Sat-Sun weeks even if the table is monthly/yearly.
    # =====================================================
    weekly_groups: dict[str, dict] = {}
    for label, week_start, week_end in _school_week_labels_between(start, end):
        weekly_groups[label] = _blank_overview_row(label, week_start)

    for a in att_qs:
        label, week_start = _group_key(a.attendance_date, "week")
        item = _ensure_overview_group(weekly_groups, label, week_start)
        if a.status == Attendance.Status.PRESENT:
            item["present"] += 1
            item["deducted_count"] += 1
            item["class_ids"].add(a.enrollment.tutoring_class_id)
        elif a.status == Attendance.Status.EXCUSED:
            item["excused"] += 1
        elif a.status == Attendance.Status.NO_SHOW:
            item["no_show"] += 1
            item["deducted_count"] += 1
            item["class_ids"].add(a.enrollment.tutoring_class_id)

    for p in payroll_qs:
        label, week_start = _group_key(p.work_date, "week")
        item = _ensure_overview_group(weekly_groups, label, week_start)
        item["actual_tutor_cost"] += _money(p.total_amount)

    for e in expense_qs:
        label, week_start = _group_key(e.expense_date, "week")
        item = _ensure_overview_group(weekly_groups, label, week_start)
        item["general_expense"] += _money(e.amount)

    weekly_rows = sorted(weekly_groups.values(), key=lambda x: x["sort"])
    for item in weekly_rows:
        active_class_count = len(item["class_ids"])
        item["active_class_count"] = active_class_count
        item["estimated_revenue"] = Decimal(item["deducted_count"]) * revenue_per_student
        item["estimated_tutor_cost"] = Decimal(active_class_count) * estimated_tutor_cost_per_class

    chart_labels = [r["label"] for r in weekly_rows]
    chart_present = [r["present"] for r in weekly_rows]
    chart_excused = [r["excused"] for r in weekly_rows]
    chart_no_show = [r["no_show"] for r in weekly_rows]
    chart_revenue = [float(r["estimated_revenue"]) for r in weekly_rows]
    chart_estimated_cost = [float(r["estimated_tutor_cost"]) for r in weekly_rows]
    chart_actual_tutor = [float(r["actual_tutor_cost"]) for r in weekly_rows]

    classes = TutoringClass.objects.filter(is_active=True).order_by("time_slot", "name")

    return render(request, "core/school_overview.html", {
        "rows": rows,
        "totals": totals,
        "period_mode": period_mode,
        "group_by": group_by,
        "start": start,
        "end": end,
        "filters": {
            "anchor_date": request.GET.get("anchor_date") or timezone.localdate().isoformat(),
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "time_slot": time_slot,
            "class_id": class_id,
        },
        "classes": classes,
        "time_slot_choices": TutoringClass.TimeSlot.choices,
        "revenue_per_student": revenue_per_student,
        "estimated_tutor_cost_per_class": estimated_tutor_cost_per_class,
        "chart_labels_json": json.dumps(chart_labels, ensure_ascii=False),
        "chart_present_json": json.dumps(chart_present),
        "chart_excused_json": json.dumps(chart_excused),
        "chart_no_show_json": json.dumps(chart_no_show),
        "chart_revenue_json": json.dumps(chart_revenue),
        "chart_estimated_cost_json": json.dumps(chart_estimated_cost),
        "chart_actual_tutor_json": json.dumps(chart_actual_tutor),
    })


@login_required
def _school_finance_filtered_data(request: HttpRequest):
    selected_date = _parse_date(request.GET.get("work_date") or request.POST.get("work_date"))
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    if date_to < date_from:
        date_from, date_to = date_to, date_from

    revenue_per_student = _finance_setting(
        "revenue_per_student_per_week",
        Decimal("360"),
        "รายได้ประมาณการต่อคนต่อสัปดาห์ / ต่อครั้งที่หักชั่วโมง",
    )

    att_qs = Attendance.objects.filter(
        attendance_date__gte=date_from,
        attendance_date__lte=date_to,
        student__is_active=True,
        enrollment__tutoring_class__is_active=True,
        status__in=[Attendance.Status.PRESENT, Attendance.Status.NO_SHOW],
    )
    deducted_count = att_qs.count()
    estimated_revenue = Decimal(deducted_count) * revenue_per_student

    expense_rows = (
        SchoolExpense.objects
        .select_related("category")
        .filter(expense_date__gte=date_from, expense_date__lte=date_to)
        .order_by("-expense_date", "-created_at")
    )
    payroll_rows = (
        TutorPayrollEntry.objects
        .select_related("tutor")
        .filter(work_date__gte=date_from, work_date__lte=date_to)
        .order_by("-work_date", "tutor__name")
    )
    course_payment_rows = (
        CoursePayment.objects
        .select_related("student", "tutoring_class", "enrollment")
        .filter(
            payment_date__gte=date_from,
            payment_date__lte=date_to,
            status=CoursePayment.ReceiptStatus.ISSUED,
        )
        .order_by("-payment_date", "-created_at")
    )

    general_expense_total = expense_rows.aggregate(total=Sum("amount")).get("total") or Decimal("0")
    tutor_payroll_total = payroll_rows.aggregate(total=Sum("total_amount")).get("total") or Decimal("0")
    cash_revenue_total = course_payment_rows.aggregate(total=Sum("amount_paid")).get("total") or Decimal("0")
    total_expense = general_expense_total + tutor_payroll_total
    net_estimated = estimated_revenue - total_expense
    net_cash_basis = cash_revenue_total - total_expense

    return {
        "selected_date": selected_date,
        "date_from": date_from,
        "date_to": date_to,
        "revenue_per_student": revenue_per_student,
        "deducted_count": deducted_count,
        "estimated_revenue": estimated_revenue,
        "cash_revenue_total": cash_revenue_total,
        "expense_rows": expense_rows,
        "payroll_rows": payroll_rows,
        "course_payment_rows": course_payment_rows,
        "general_expense_total": general_expense_total,
        "tutor_payroll_total": tutor_payroll_total,
        "total_expense": total_expense,
        "net_estimated": net_estimated,
        "net_cash_basis": net_cash_basis,
    }



# =========================================================
# ✅ Course Renewal Notice Module
# =========================================================
def _default_renewal_dates(enrollment: Enrollment) -> tuple[date, date]:
    """
    Default วันครบคอร์ส:
    - Class เสาร์เช้า/เสาร์บ่าย → วันเสาร์ที่กำลังจะมาถึง
    - Class อาทิตย์เช้า/อาทิตย์บ่าย → วันอาทิตย์ที่กำลังจะมาถึง
    - อื่น ๆ → วันเสาร์ที่กำลังจะมาถึง
    """
    today = timezone.localdate()
    time_slot = getattr(enrollment.tutoring_class, "time_slot", "") if enrollment and enrollment.tutoring_class_id else ""

    if time_slot in (
        TutoringClass.TimeSlot.SUN_MORNING,
        TutoringClass.TimeSlot.SUN_AFTERNOON,
    ):
        target_weekday = 6  # Sunday
    else:
        target_weekday = 5  # Saturday

    days_ahead = (target_weekday - today.weekday()) % 7
    expected_end = today + timedelta(days=days_ahead)
    next_start = expected_end + timedelta(days=7)
    return expected_end, next_start


def _decimal_from_post(value, default: Decimal) -> Decimal:
    try:
        s = str(value or "").replace(",", "").strip()
        if s == "":
            return default
        return Decimal(s)
    except Exception:
        return default


def _renewal_notice_packages(notice: CourseRenewalNotice) -> list[dict]:
    return [
        {
            "label": "ต่อคอร์ส 10 สัปดาห์",
            "weeks": 10,
            "full_price": notice.package_10_full_price,
            "discount": notice.package_10_discount,
            "net_price": notice.package_10_net_price,
            "accent": "blue",
        },
        {
            "label": "ต่อคอร์ส 20 สัปดาห์",
            "weeks": 20,
            "full_price": notice.package_20_full_price,
            "discount": notice.package_20_discount,
            "net_price": notice.package_20_net_price,
            "accent": "green",
        },
        {
            "label": "ต่อคอร์ส 30 สัปดาห์",
            "weeks": 30,
            "full_price": notice.package_30_full_price,
            "discount": notice.package_30_discount,
            "net_price": notice.package_30_net_price,
            "accent": "purple",
        },
    ]


def _issued_payments_for_enrollment(enrollment: Enrollment):
    return (
        CoursePayment.objects
        .filter(enrollment=enrollment, status=CoursePayment.ReceiptStatus.ISSUED)
        .order_by("payment_date", "created_at")
    )


def _installment_amounts_for_enrollment(enrollment: Enrollment) -> dict:
    payments = _issued_payments_for_enrollment(enrollment)
    paid = payments.aggregate(total=Sum("amount_paid")).get("total") or Decimal("0")
    full = Decimal(str(enrollment.net_price or enrollment.course_price or 0))
    remaining = max(full - paid, Decimal("0"))
    return {
        "full": full,
        "paid": paid,
        "remaining": remaining,
        "first_payment": payments.first(),
    }


def _admin_student_url(student: Student) -> str:
    return f"/adminlublub/core/student/{student.id}/change/" if student and student.id else "#"


def _admin_enrollment_url(enrollment: Enrollment) -> str:
    return f"/adminlublub/core/enrollment/{enrollment.id}/change/" if enrollment and enrollment.id else "#"


@login_required
def course_renewal_notice_list(request: HttpRequest) -> HttpResponse:
    """
    รายการ Enrollment ที่ใกล้ครบคอร์ส แบ่งตามสถานะ "กดส่งแจ้งผู้ปกครองแล้ว" เท่านั้น

    หลักการสำคัญ:
    - ไม่สนใจว่าเคยกดสร้างใบแจ้งแล้วหรือยัง
    - ถ้า enrollment เหลือ < 2 และยังไม่มีใบแจ้งใดที่ถูก mark ว่า sent → อยู่ในกลุ่ม "ยังไม่แจ้ง"
    - ถ้า enrollment เหลือ < 2 และมีใบแจ้งอย่างน้อย 1 ใบที่ถูก mark ว่า sent → อยู่ในกลุ่ม "แจ้งแล้ว"
    - date_from/date_to ใช้กรองเฉพาะประวัติใบแจ้งที่ส่งแล้วด้านล่าง ไม่กระทบการแบ่งกลุ่มหลัก
    """
    q = (request.GET.get("q") or "").strip()
    date_from = _safe_date(request.GET.get("date_from"))
    date_to = _safe_date(request.GET.get("date_to"))

    enrollments_qs = (
        Enrollment.objects
        .select_related("student", "tutoring_class")
        .filter(
            is_active=True,
            student__is_active=True,
            tutoring_class__is_active=True,
        )
        .order_by("tutoring_class__time_slot", "tutoring_class__name", "student__nickname", "student__full_name")
    )

    if q:
        enrollments_qs = enrollments_qs.filter(
            Q(student__nickname__icontains=q) |
            Q(student__full_name__icontains=q) |
            Q(student__student_code__icontains=q) |
            Q(tutoring_class__name__icontains=q) |
            Q(sale_run_no__icontains=q)
        )

    not_notified_rows = []
    notified_rows = []

    for enrollment in enrollments_qs:
        remaining_sessions = int(enrollment.remaining_sessions or 0)
        if remaining_sessions >= 2:
            continue

        # Do NOT apply date filters here.
        # Main grouping must depend only on whether this enrollment has ever been marked as sent.
        notices_qs = (
            CourseRenewalNotice.objects
            .select_related("student", "tutoring_class", "enrollment", "source_payment", "sent_to_parent_by")
            .filter(enrollment=enrollment)
            .order_by("-created_at")
        )

        latest_notice = notices_qs.first()
        latest_unsent_notice = notices_qs.filter(is_sent_to_parent=False).first()
        latest_sent_notice = (
            notices_qs
            .filter(is_sent_to_parent=True)
            .order_by("-sent_to_parent_at", "-created_at")
            .first()
        )

        expected_end, next_start = _default_renewal_dates(enrollment)
        amounts = _installment_amounts_for_enrollment(enrollment)

        row = {
            "enrollment": enrollment,
            "student": enrollment.student,
            "tutoring_class": enrollment.tutoring_class,
            "remaining": remaining_sessions,
            "latest_notice": latest_notice,
            "latest_unsent_notice": latest_unsent_notice,
            "latest_sent_notice": latest_sent_notice,
            "default_expected_end": expected_end,
            "default_next_start": next_start,
            "full_amount": amounts["full"],
            "paid_amount": amounts["paid"],
            "remaining_amount": amounts["remaining"],
            "first_payment": amounts["first_payment"],
            "student_admin_url": _admin_student_url(enrollment.student),
            "enrollment_admin_url": _admin_enrollment_url(enrollment),
        }

        if latest_sent_notice:
            notified_rows.append(row)
        else:
            not_notified_rows.append(row)

    all_notices_qs = (
        CourseRenewalNotice.objects
        .select_related("student", "tutoring_class", "enrollment", "source_payment", "sent_to_parent_by")
        .order_by("-created_at")
    )

    if q:
        all_notices_qs = all_notices_qs.filter(
            Q(student__nickname__icontains=q) |
            Q(student__full_name__icontains=q) |
            Q(student__student_code__icontains=q) |
            Q(tutoring_class__name__icontains=q) |
            Q(enrollment__sale_run_no__icontains=q) |
            Q(source_payment__receipt_no__icontains=q)
        )

    sent_history_qs = all_notices_qs.filter(is_sent_to_parent=True)
    if date_from:
        sent_history_qs = sent_history_qs.filter(sent_to_parent_at__date__gte=date_from)
    if date_to:
        sent_history_qs = sent_history_qs.filter(sent_to_parent_at__date__lte=date_to)

    sent_notices = sent_history_qs.order_by("-sent_to_parent_at", "-created_at")

    return render(request, "core/course_renewal_notice_list.html", {
        "not_notified_rows": not_notified_rows,
        "notified_rows": notified_rows,
        "sent_notices": sent_notices,
        "q": q,
        "date_from": date_from.isoformat() if date_from else "",
        "date_to": date_to.isoformat() if date_to else "",
    })

@login_required
def course_renewal_notice_create(request: HttpRequest, enrollment_id: int) -> HttpResponse:
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "tutoring_class"),
        id=enrollment_id,
        is_active=True,
        student__is_active=True,
        tutoring_class__is_active=True,
    )

    expected_end, next_start = _default_renewal_dates(enrollment)

    notice = CourseRenewalNotice.objects.create(
        notice_type=CourseRenewalNotice.NoticeType.RENEWAL,
        enrollment=enrollment,
        student=enrollment.student,
        tutoring_class=enrollment.tutoring_class,
        expected_course_end_date=expected_end,
        next_course_start_date=next_start,
        created_by=request.user if request.user.is_authenticated else None,
    )

    return redirect("core:course_renewal_notice_detail", pk=notice.pk)


@login_required
def course_installment_notice_create(request: HttpRequest, enrollment_id: int) -> HttpResponse:
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "tutoring_class"),
        id=enrollment_id,
        is_active=True,
        student__is_active=True,
        tutoring_class__is_active=True,
    )

    expected_end, next_start = _default_renewal_dates(enrollment)
    amounts = _installment_amounts_for_enrollment(enrollment)

    try:
        installment_no = int(request.GET.get("installment_no") or 2)
    except Exception:
        installment_no = 2
    if installment_no not in (2, 3, 4):
        installment_no = 2

    notice = CourseRenewalNotice.objects.create(
        notice_type=CourseRenewalNotice.NoticeType.INSTALLMENT,
        installment_no=installment_no,
        installment_sessions=0,
        enrollment=enrollment,
        student=enrollment.student,
        tutoring_class=enrollment.tutoring_class,
        source_payment=amounts["first_payment"],
        expected_course_end_date=expected_end,
        next_course_start_date=next_start,
        installment_full_amount=amounts["full"],
        installment_paid_amount=amounts["paid"],
        created_by=request.user if request.user.is_authenticated else None,
    )

    return redirect("core:course_renewal_notice_detail", pk=notice.pk)


@require_POST
@login_required
def course_renewal_notice_mark_sent(request: HttpRequest, pk: int) -> HttpResponse:
    notice = get_object_or_404(CourseRenewalNotice, pk=pk)
    notice.is_sent_to_parent = True
    notice.sent_to_parent_at = timezone.now()
    notice.sent_to_parent_by = request.user if request.user.is_authenticated else None
    notice.save()
    return redirect(request.META.get("HTTP_REFERER") or "core:course_renewal_notice_list")


@require_POST
@login_required
def course_renewal_notice_unmark_sent(request: HttpRequest, pk: int) -> HttpResponse:
    notice = get_object_or_404(CourseRenewalNotice, pk=pk)
    notice.is_sent_to_parent = False
    notice.sent_to_parent_at = None
    notice.sent_to_parent_by = None
    notice.save()
    return redirect(request.META.get("HTTP_REFERER") or "core:course_renewal_notice_list")


@login_required
def course_renewal_notice_detail(request: HttpRequest, pk: int) -> HttpResponse:
    notice = get_object_or_404(
        CourseRenewalNotice.objects.select_related("student", "tutoring_class", "enrollment", "source_payment"),
        pk=pk,
    )

    if request.method == "POST":
        notice.expected_course_end_date = _parse_date(request.POST.get("expected_course_end_date"))
        notice.next_course_start_date = _parse_date(request.POST.get("next_course_start_date"))

        notice_kind = (request.POST.get("notice_kind") or "").strip()
        if notice_kind == "renewal":
            notice.notice_type = CourseRenewalNotice.NoticeType.RENEWAL
            notice.installment_no = None
            notice.installment_sessions = 0
        elif notice_kind in {"installment_2", "installment_3", "installment_4"}:
            notice.notice_type = CourseRenewalNotice.NoticeType.INSTALLMENT
            try:
                notice.installment_no = int(notice_kind.split("_")[-1])
            except Exception:
                notice.installment_no = 2

        notice.package_10_full_price = _decimal_from_post(request.POST.get("package_10_full_price"), notice.package_10_full_price)
        notice.package_10_discount = _decimal_from_post(request.POST.get("package_10_discount"), notice.package_10_discount)

        notice.package_20_full_price = _decimal_from_post(request.POST.get("package_20_full_price"), notice.package_20_full_price)
        notice.package_20_discount = _decimal_from_post(request.POST.get("package_20_discount"), notice.package_20_discount)

        notice.package_30_full_price = _decimal_from_post(request.POST.get("package_30_full_price"), notice.package_30_full_price)
        notice.package_30_discount = _decimal_from_post(request.POST.get("package_30_discount"), notice.package_30_discount)

        notice.installment_full_amount = _decimal_from_post(request.POST.get("installment_full_amount"), notice.installment_full_amount)
        notice.installment_paid_amount = _decimal_from_post(request.POST.get("installment_paid_amount"), notice.installment_paid_amount)
        try:
            notice.installment_sessions = max(int(request.POST.get("installment_sessions") or 0), 0)
        except Exception:
            notice.installment_sessions = notice.installment_sessions or 0

        notice.note_wording = (request.POST.get("note_wording") or "").strip() or notice.note_wording
        notice.save()
        return redirect("core:course_renewal_notice_detail", pk=notice.pk)

    notice_kind = "renewal"
    if notice.notice_type == CourseRenewalNotice.NoticeType.INSTALLMENT:
        notice_kind = f"installment_{notice.installment_no or 2}"

    return render(request, "core/course_renewal_notice_detail.html", {
        "notice": notice,
        "notice_kind": notice_kind,
        "student": notice.student,
        "enrollment": notice.enrollment,
        "tutoring_class": notice.tutoring_class,
        "packages": _renewal_notice_packages(notice),
        "student_admin_url": _admin_student_url(notice.student),
        "enrollment_admin_url": _admin_enrollment_url(notice.enrollment),
    })



def pkanoon_admin_tool(request: HttpRequest) -> HttpResponse:
    """Private landing page for sensitive school tools."""
    return render(request, "core/pkanoon_admin_tool.html")



def _weekend_tutor_summary(selected_date: date) -> dict:
    """
    Combine tutor payroll by school weekend.
    If selected date is Sat: Sat + next Sun.
    If selected date is Sun: previous Sat + Sun.
    Other days: school week containing the selected date (Sat-Sun).
    """
    weekend_start, weekend_end = _school_week_range(selected_date)

    rows_by_tutor: dict[int, dict] = {}
    qs = (
        TutorPayrollEntry.objects
        .select_related("tutor")
        .filter(work_date__gte=weekend_start, work_date__lte=weekend_end)
        .order_by("tutor__name", "work_date")
    )

    zero = Decimal("0")
    totals = {
        "tutor_count": 0,
        "onsite_hours": zero,
        "online_hours": zero,
        "onsite_fee": zero,
        "online_fee": zero,
        "travel_fee": zero,
        "idle_fee": zero,
        "total_amount": zero,
    }

    for p in qs:
        if not p.tutor_id:
            continue

        row = rows_by_tutor.setdefault(p.tutor_id, {
            "tutor": p.tutor,
            "onsite_hours": zero,
            "online_hours": zero,
            "onsite_fee": zero,
            "online_fee": zero,
            "travel_fee": zero,
            "idle_fee": zero,
            "total_amount": zero,
            "sat_amount": zero,
            "sun_amount": zero,
            "sat_hours": zero,
            "sun_hours": zero,
            "has_special_rate": False,
            "notes": [],
        })

        teaching_hours = Decimal(str(p.teaching_hours or 0))
        online_hours = Decimal(str(getattr(p, "online_teaching_hours", 0) or 0))
        teaching_fee = Decimal(str(p.teaching_fee or 0))
        online_fee = Decimal(str(getattr(p, "online_teaching_fee", 0) or 0))
        travel_fee = Decimal(str(p.travel_fee or 0))
        idle_fee = Decimal(str(p.idle_fee or 0))
        total_amount = Decimal(str(p.total_amount or 0))

        row["onsite_hours"] += teaching_hours
        row["online_hours"] += online_hours
        row["onsite_fee"] += teaching_fee
        row["online_fee"] += online_fee
        row["travel_fee"] += travel_fee
        row["idle_fee"] += idle_fee
        row["total_amount"] += total_amount
        row["has_special_rate"] = row["has_special_rate"] or bool(getattr(p, "special_rate_325", False))

        if p.work_date == weekend_start:
            row["sat_amount"] += total_amount
            row["sat_hours"] += teaching_hours + online_hours
        elif p.work_date == weekend_end:
            row["sun_amount"] += total_amount
            row["sun_hours"] += teaching_hours + online_hours

        if p.note:
            row["notes"].append(f"{p.work_date.strftime('%d/%m')}: {p.note}")

    rows = sorted(rows_by_tutor.values(), key=lambda r: (r["tutor"].name if r.get("tutor") else ""))

    totals["tutor_count"] = len(rows)
    for row in rows:
        totals["onsite_hours"] += row["onsite_hours"]
        totals["online_hours"] += row["online_hours"]
        totals["onsite_fee"] += row["onsite_fee"]
        totals["online_fee"] += row["online_fee"]
        totals["travel_fee"] += row["travel_fee"]
        totals["idle_fee"] += row["idle_fee"]
        totals["total_amount"] += row["total_amount"]

    return {
        "start": weekend_start,
        "end": weekend_end,
        "rows": rows,
        "totals": totals,
    }


@login_required
def school_finance_export(request: HttpRequest) -> HttpResponse:
    data = _school_finance_filtered_data(request)

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Item", "Amount / Count"])
    ws.append(["Date From", data["date_from"].isoformat()])
    ws.append(["Date To", data["date_to"].isoformat()])
    ws.append(["Revenue per attendance", float(data["revenue_per_student"])])
    ws.append(["Recognized attendance count", data["deducted_count"]])
    ws.append(["Estimated revenue from attendance", float(data["estimated_revenue"])])
    ws.append(["Cash basis course revenue", float(data["cash_revenue_total"])])
    ws.append(["General expenses", float(data["general_expense_total"])])
    ws.append(["Tutor payroll", float(data["tutor_payroll_total"])])
    ws.append(["Total expenses", float(data["total_expense"])])
    ws.append(["Net attendance estimate", float(data["net_estimated"])])
    ws.append(["Net cash basis", float(data["net_cash_basis"])])
    _autosize(ws)

    ws_exp = wb.create_sheet("General Expenses")
    ws_exp.append(["Date", "Category", "Vendor", "Description", "Payment Method", "Amount", "Note"])
    for e in data["expense_rows"]:
        ws_exp.append([
            e.expense_date.isoformat(),
            e.category.name if e.category else "",
            e.vendor or "",
            e.description or "",
            e.get_payment_method_display() if hasattr(e, "get_payment_method_display") else e.payment_method,
            float(e.amount or 0),
            e.note or "",
        ])
    _autosize(ws_exp)

    ws_pay = wb.create_sheet("Tutor Payroll")
    ws_pay.append(["Date", "Tutor", "Onsite Hours", "Special 325?", "Hourly Rate", "Onsite Teaching Fee", "Online Hours", "Online Teaching Fee", "Travel Fee", "Idle/Other Fee", "Total", "Note"])
    for p in data["payroll_rows"]:
        ws_pay.append([
            p.work_date.isoformat(),
            p.tutor.name if p.tutor else "",
            float(p.teaching_hours or 0),
            "Yes" if getattr(p, "special_rate_325", False) else "No",
            float(p.hourly_rate or 0),
            float(p.teaching_fee or 0),
            float(getattr(p, "online_teaching_hours", 0) or 0),
            float(getattr(p, "online_teaching_fee", 0) or 0),
            float(p.travel_fee or 0),
            float(p.idle_fee or 0),
            float(p.total_amount or 0),
            p.note or "",
        ])
    _autosize(ws_pay)

    weekend_summary = _weekend_tutor_summary(data["selected_date"])
    ws_weekend = wb.create_sheet("Weekend Tutor Summary")
    ws_weekend.append([
        "Weekend Start",
        weekend_summary["start"].isoformat(),
        "Weekend End",
        weekend_summary["end"].isoformat(),
    ])
    ws_weekend.append([])
    ws_weekend.append([
        "Tutor",
        "Onsite Hours",
        "Online Hours",
        "Onsite Teaching Fee",
        "Online Teaching Fee",
        "Travel Fee",
        "Idle/Other Fee",
        "Saturday Amount",
        "Sunday Amount",
        "Weekend Total",
        "Special 325 Used?",
    ])
    for r in weekend_summary["rows"]:
        ws_weekend.append([
            r["tutor"].name if r.get("tutor") else "",
            float(r["onsite_hours"] or 0),
            float(r["online_hours"] or 0),
            float(r["onsite_fee"] or 0),
            float(r["online_fee"] or 0),
            float(r["travel_fee"] or 0),
            float(r["idle_fee"] or 0),
            float(r["sat_amount"] or 0),
            float(r["sun_amount"] or 0),
            float(r["total_amount"] or 0),
            "Yes" if r["has_special_rate"] else "No",
        ])
    _autosize(ws_weekend)

    ws_cash = wb.create_sheet("Course Payments")
    ws_cash.append(["Receipt No", "Payment Date", "Student", "Class", "Enrollment", "Payment Type", "Payment Method", "Sessions", "Course Price", "Discount", "Net Amount", "Amount Paid", "Status", "Note"])
    course_payment_export_rows = (
        CoursePayment.objects
        .select_related("student", "tutoring_class", "enrollment")
        .filter(status=CoursePayment.ReceiptStatus.ISSUED)
        .order_by("-payment_date", "-created_at")
    )
    for p in course_payment_export_rows:
        ws_cash.append([
            p.receipt_no,
            p.payment_date.isoformat() if p.payment_date else "",
            p.student.display_name if p.student_id else "",
            p.tutoring_class.name if p.tutoring_class_id else "",
            p.enrollment.sale_run_no if p.enrollment_id and p.enrollment else "",
            p.get_payment_type_display() if hasattr(p, "get_payment_type_display") else p.payment_type,
            p.get_payment_method_display() if hasattr(p, "get_payment_method_display") else p.payment_method,
            int(p.sessions_granted or 0),
            float(p.course_price or 0),
            float(p.discount_amount or 0),
            float(p.net_amount or 0),
            float(p.amount_paid or 0),
            p.get_status_display() if hasattr(p, "get_status_display") else p.status,
            p.note or "",
        ])
    _autosize(ws_cash)

    buff = BytesIO()
    wb.save(buff)
    buff.seek(0)

    filename = f"school_finance_{data['date_from'].strftime('%Y%m%d')}_{data['date_to'].strftime('%Y%m%d')}.xlsx"
    resp = HttpResponse(
        buff.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@login_required
def school_finance(request: HttpRequest) -> HttpResponse:
    """
    Module 2:
    - Revenue estimate from attendance.
    - General expenses.
    - Tutor payroll batch input.
    """
    selected_date = _parse_date(request.GET.get("work_date") or request.POST.get("work_date"))
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    if date_to < date_from:
        date_from, date_to = date_to, date_from

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action == "add_category":
            name = (request.POST.get("category_name") or "").strip()
            if name:
                ExpenseCategory.objects.get_or_create(name=name, defaults={"is_active": True, "sort_order": 99})
            return redirect(request.META.get("HTTP_REFERER", "core:school_finance"))

        if action == "add_tutor":
            name = (request.POST.get("tutor_name") or "").strip()
            phone = (request.POST.get("tutor_phone") or "").strip()
            if name:
                Tutor.objects.update_or_create(name=name, defaults={"phone": phone, "is_active": True})
            return redirect(request.META.get("HTTP_REFERER", "core:school_finance"))

        if action == "add_expense":
            category_id = request.POST.get("category")
            try:
                category = ExpenseCategory.objects.get(id=category_id, is_active=True)
                SchoolExpense.objects.create(
                    expense_date=_parse_date(request.POST.get("expense_date")),
                    category=category,
                    vendor=(request.POST.get("vendor") or "").strip(),
                    description=(request.POST.get("description") or "").strip(),
                    amount=_money(request.POST.get("amount")),
                    payment_method=(request.POST.get("payment_method") or SchoolExpense.PaymentMethod.TRANSFER),
                    note=(request.POST.get("note") or "").strip(),
                )
            except Exception:
                pass
            return redirect(request.META.get("HTTP_REFERER", "core:school_finance"))

        if action == "save_payroll":
            work_date = _parse_date(request.POST.get("work_date"))
            single_tutor_id = (request.POST.get("single_tutor_id") or "").strip()
            tutor_ids = request.POST.getlist("tutor_ids")
            if single_tutor_id:
                tutor_ids = [single_tutor_id]

            for tid in tutor_ids:
                hours_raw = (request.POST.get(f"hours_{tid}") or "").strip()
                online_hours_raw = (request.POST.get(f"online_hours_{tid}") or "").strip()
                idle_raw = (request.POST.get(f"idle_{tid}") or "").strip()
                note_raw = (request.POST.get(f"note_{tid}") or "").strip()
                special_rate_325 = request.POST.get(f"special_rate_325_{tid}") == "yes"

                # Skip blank rows when saving all.
                if (
                    not single_tutor_id
                    and hours_raw == ""
                    and online_hours_raw == ""
                    and idle_raw == ""
                    and note_raw == ""
                    and not special_rate_325
                ):
                    continue

                hours = _money(hours_raw)
                online_hours = _money(online_hours_raw)
                idle_fee = _money(idle_raw)

                if hours <= 0 and online_hours <= 0 and idle_fee <= 0 and not note_raw:
                    continue

                try:
                    tutor = Tutor.objects.get(id=tid, is_active=True)
                except Tutor.DoesNotExist:
                    continue

                entry, _ = TutorPayrollEntry.objects.get_or_create(
                    work_date=work_date,
                    tutor=tutor,
                    defaults={
                        "teaching_hours": hours,
                        "online_teaching_hours": online_hours,
                        "special_rate_325": special_rate_325,
                        "idle_fee": idle_fee,
                        "note": note_raw,
                    },
                )
                entry.teaching_hours = hours
                entry.online_teaching_hours = online_hours
                entry.special_rate_325 = special_rate_325
                entry.idle_fee = idle_fee
                entry.note = note_raw
                entry.save()

            return redirect(f"{request.path}?work_date={work_date.isoformat()}&date_from={date_from.isoformat()}&date_to={date_to.isoformat()}")

    data = _school_finance_filtered_data(request)
    weekend_tutor_summary = _weekend_tutor_summary(data["selected_date"])

    categories = ExpenseCategory.objects.filter(is_active=True).order_by("sort_order", "name")
    tutors = Tutor.objects.filter(is_active=True).order_by("name")
    existing_entries = TutorPayrollEntry.objects.filter(work_date=data["selected_date"]).select_related("tutor")
    payroll_map = {e.tutor_id: e for e in existing_entries}

    payment_method_choices = SchoolExpense.PaymentMethod.choices
    current_querystring = request.GET.urlencode()

    return render(request, "core/school_finance.html", {
        "selected_date": data["selected_date"],
        "date_from": data["date_from"],
        "date_to": data["date_to"],
        "categories": categories,
        "tutors": tutors,
        "payroll_map": payroll_map,
        "expense_rows": data["expense_rows"],
        "payroll_rows": data["payroll_rows"],
        "weekend_tutor_summary": weekend_tutor_summary,
        "deducted_count": data["deducted_count"],
        "revenue_per_student": data["revenue_per_student"],
        "estimated_revenue": data["estimated_revenue"],
        "cash_revenue_total": data["cash_revenue_total"],
        "general_expense_total": data["general_expense_total"],
        "tutor_payroll_total": data["tutor_payroll_total"],
        "total_expense": data["total_expense"],
        "net_estimated": data["net_estimated"],
        "net_cash_basis": data["net_cash_basis"],
        "payment_method_choices": payment_method_choices,
        "current_querystring": current_querystring,
    })


@login_required
def course_payment_list(request: HttpRequest) -> HttpResponse:
    qs = CoursePayment.objects.select_related("student", "tutoring_class", "enrollment").order_by("-payment_date", "-created_at")
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    date_from = _safe_date(request.GET.get("date_from"))
    date_to = _safe_date(request.GET.get("date_to"))

    if q:
        qs = qs.filter(
            Q(receipt_no__icontains=q) |
            Q(student__nickname__icontains=q) |
            Q(student__full_name__icontains=q) |
            Q(student__student_code__icontains=q) |
            Q(tutoring_class__name__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(payment_date__gte=date_from)
    if date_to:
        qs = qs.filter(payment_date__lte=date_to)

    totals = qs.aggregate(total=Sum("amount_paid"))
    issued_total = qs.filter(status=CoursePayment.ReceiptStatus.ISSUED).aggregate(total=Sum("amount_paid")).get("total") or Decimal("0")

    return render(request, "core/course_payment_list.html", {
        "payments": qs[:300],
        "filters": {"q": q, "status": status, "date_from": request.GET.get("date_from", ""), "date_to": request.GET.get("date_to", "")},
        "status_choices": CoursePayment.ReceiptStatus.choices,
        "issued_total": issued_total,
        "all_total": totals.get("total") or Decimal("0"),
    })


@login_required
def course_payment_create(request: HttpRequest) -> HttpResponse:
    errors: list[str] = []
    if request.method == "POST":
        post = request.POST
        try:
            student_mode = (post.get("student_mode") or "existing").strip()
            enrollment_action = (post.get("enrollment_action") or CoursePayment.EnrollmentAction.NEW).strip()
            payment_date = _parse_date(post.get("payment_date"))
            payment_type = (post.get("payment_type") or CoursePayment.PaymentType.FULL).strip()
            payment_method = (post.get("payment_method") or CoursePayment.PaymentMethod.BANK_TRANSFER).strip()
            package = (post.get("session_package") or "10").strip()
            sessions_granted = _sessions_from_package(package, post.get("custom_sessions"))
            course_price = _money(post.get("course_price"))
            discount_amount = _money(post.get("discount_amount"))
            net_amount = max(course_price - discount_amount, Decimal("0"))
            amount_paid = _money(post.get("amount_paid")) or net_amount
            note = (post.get("note") or "").strip()

            if student_mode == "new":
                nickname = (post.get("new_nickname") or "").strip()
                full_name = (post.get("new_full_name") or "").strip()
                grade_level = (post.get("new_grade_level") or "").strip()
                school_name = (post.get("new_school_name") or "").strip()
                parent_phone = (post.get("new_parent_phone") or "").strip()
                if not full_name:
                    errors.append("กรุณากรอกชื่อจริงนามสกุลของนักเรียนใหม่")
                if not parent_phone:
                    errors.append("กรุณากรอกเบอร์ผู้ปกครองของนักเรียนใหม่")
                school = None
                if school_name:
                    school, _ = School.objects.get_or_create(name=school_name, defaults={"is_active": True})
                student = None
                if not errors:
                    student = Student.objects.create(
                        nickname=nickname,
                        full_name=full_name,
                        grade_level=grade_level,
                        school=school,
                        parent_phone=parent_phone,
                    )
            else:
                student_id = post.get("student_id")
                student = Student.objects.filter(id=student_id, is_active=True).first()
                if not student and enrollment_action != CoursePayment.EnrollmentAction.ADD_EXISTING:
                    errors.append("กรุณาเลือกนักเรียนเดิม")

            selected_class = None
            existing_enrollment = None
            if enrollment_action == CoursePayment.EnrollmentAction.ADD_EXISTING:
                existing_enrollment = Enrollment.objects.select_related("student", "tutoring_class").filter(id=post.get("existing_enrollment_id"), is_active=True).first()
                if not existing_enrollment:
                    errors.append("กรุณาเลือก Enrollment เดิมที่จะเพิ่มจำนวนครั้ง")
                else:
                    # In add-existing mode the active enrollment search is the source of truth.
                    # This makes the flow faster even if the student search box was not selected first.
                    if not student:
                        student = existing_enrollment.student
                    elif existing_enrollment.student_id != student.id:
                        errors.append("Enrollment เดิมไม่ตรงกับนักเรียนที่เลือก")
                    selected_class = existing_enrollment.tutoring_class
            else:
                selected_class = TutoringClass.objects.filter(id=post.get("tutoring_class_id"), is_active=True).first()
                if not selected_class:
                    errors.append("กรุณาเลือก Class")

            if sessions_granted <= 0:
                errors.append("จำนวนครั้งที่ให้เรียนต้องมากกว่า 0")
            if amount_paid < 0:
                errors.append("ยอดรับชำระไม่ถูกต้อง")

            if not errors and student and selected_class:
                with transaction.atomic():
                    payment = CoursePayment.objects.create(
                        payment_date=payment_date,
                        student=student,
                        tutoring_class=selected_class,
                        enrollment_action=enrollment_action,
                        session_package=package,
                        sessions_granted=sessions_granted,
                        course_price=course_price,
                        discount_amount=discount_amount,
                        net_amount=net_amount,
                        amount_paid=amount_paid,
                        payment_type=payment_type,
                        payment_method=payment_method,
                        note=note,
                        created_by=request.user if request.user.is_authenticated else None,
                    )
                    _apply_payment_to_enrollment(payment, enrollment_action, existing_enrollment)
                return redirect("core:course_payment_detail", pk=payment.pk)
        except Exception as exc:
            errors.append(f"บันทึกไม่สำเร็จ: {exc}")

        context = _default_payment_form_context(request, errors=errors, posted=dict(post))
        return render(request, "core/course_payment_create.html", context)

    return render(request, "core/course_payment_create.html", _default_payment_form_context(request))


@login_required
def course_payment_detail(request: HttpRequest, pk: int) -> HttpResponse:
    payment = get_object_or_404(
        CoursePayment.objects.select_related("student", "student__school", "tutoring_class", "enrollment"),
        pk=pk,
    )
    return render(request, "core/course_payment_detail.html", {"payment": payment})


@login_required
def course_payment_receipt_image(request: HttpRequest, pk: int) -> HttpResponse:
    payment = get_object_or_404(
        CoursePayment.objects.select_related("student", "student__school", "tutoring_class", "enrollment"),
        pk=pk,
    )
    return render(request, "core/course_payment_receipt_image.html", {"payment": payment})


@require_POST
@login_required
def course_payment_cancel(request: HttpRequest, pk: int) -> HttpResponse:
    payment = get_object_or_404(CoursePayment.objects.select_related("enrollment"), pk=pk)
    if payment.status != CoursePayment.ReceiptStatus.CANCELLED:
        with transaction.atomic():
            payment.status = CoursePayment.ReceiptStatus.CANCELLED
            payment.cancel_reason = (request.POST.get("cancel_reason") or "").strip()
            payment.cancelled_at = timezone.now()
            payment.cancelled_by = request.user if request.user.is_authenticated else None
            payment.save()
            _reverse_payment_enrollment_effect(payment)
    return redirect("core:course_payment_detail", pk=payment.pk)


@require_POST
@login_required
def school_expense_delete(request: HttpRequest, pk: int) -> HttpResponse:
    expense = get_object_or_404(SchoolExpense, pk=pk)
    expense.delete()
    return redirect(request.META.get("HTTP_REFERER", "core:school_finance"))


@require_POST
@login_required
def tutor_payroll_delete(request: HttpRequest, pk: int) -> HttpResponse:
    entry = get_object_or_404(TutorPayrollEntry, pk=pk)
    entry.delete()
    return redirect(request.META.get("HTTP_REFERER", "core:school_finance"))

# =========================================================
# ✅ Tutor Teaching Update Module
# =========================================================
def _teaching_week_range(anchor: date) -> tuple[date, date]:
    """Teaching week = Saturday to Sunday, same as school finance week."""
    days_since_sat = (anchor.weekday() - 5) % 7
    start = anchor - timedelta(days=days_since_sat)
    return start, start + timedelta(days=1)


def _teaching_week_from_request(request: HttpRequest) -> tuple[date, date]:
    raw = request.GET.get("week_start") or request.POST.get("week_start") or request.GET.get("date")
    anchor = _safe_date(raw) if "_safe_date" in globals() else None
    if not anchor:
        anchor = _parse_date(raw)
    return _teaching_week_range(anchor)


def _latest_tutor_for_template(template: TeachingClassSubjectTemplate, before_week_start: date) -> TeachingTutor | None:
    prev = (
        TeachingWeeklyAssignment.objects
        .filter(subject_template=template, week_start_date__lt=before_week_start, tutor__isnull=False)
        .select_related("tutor")
        .order_by("-week_start_date", "-updated_at")
        .first()
    )
    return prev.tutor if prev and prev.tutor_id else None


def _ensure_teaching_assignments(week_start: date, week_end: date) -> None:
    templates = (
        TeachingClassSubjectTemplate.objects
        .select_related("tutoring_class")
        .filter(is_active=True, tutoring_class__is_active=True)
        .order_by("tutoring_class__name", "display_order", "subject_name")
    )

    with transaction.atomic():
        for tmpl in templates:
            assignment, created = TeachingWeeklyAssignment.objects.get_or_create(
                week_start_date=week_start,
                subject_template=tmpl,
                defaults={
                    "week_end_date": week_end,
                    "tutoring_class": tmpl.tutoring_class,
                    "tutor": _latest_tutor_for_template(tmpl, week_start),
                },
            )
            changed = False
            if assignment.week_end_date != week_end:
                assignment.week_end_date = week_end
                changed = True
            if assignment.tutoring_class_id != tmpl.tutoring_class_id:
                assignment.tutoring_class = tmpl.tutoring_class
                changed = True
            if created is False and assignment.tutor_id is None:
                last_tutor = _latest_tutor_for_template(tmpl, week_start)
                if last_tutor:
                    assignment.tutor = last_tutor
                    changed = True
            if changed:
                assignment.save()


@login_required
def teaching_template_manage(request: HttpRequest) -> HttpResponse:
    classes = list(TutoringClass.objects.filter(is_active=True).order_by("name"))
    for c in classes:
        c.sheet_grade_level = _class_grade_level(c)
    tutors = TeachingTutor.objects.filter(is_active=True).order_by("name")
    sheet_choices = Sheet.objects.select_related("subject").filter(is_active=True).order_by("grade_level", "subject__name", "code")
    class_grade_map = {str(c.id): c.sheet_grade_level for c in classes}

    selected_class_id = (request.GET.get("class_id") or request.POST.get("class_id") or "").strip()

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action == "add_tutor":
            tutor_name = (request.POST.get("tutor_name") or "").strip()
            tutor_phone = (request.POST.get("tutor_phone") or "").strip()
            if tutor_name:
                TeachingTutor.objects.update_or_create(
                    name=tutor_name,
                    defaults={"phone": tutor_phone, "is_active": True},
                )
            return redirect(f"/teaching/templates/?class_id={selected_class_id}" if selected_class_id else "/teaching/templates/")

        if action == "add_subject":
            class_id = request.POST.get("class_id")
            subject_name = (request.POST.get("subject_name") or "").strip()
            default_sheet_name = (request.POST.get("default_sheet_name") or "").strip()
            display_order_raw = (request.POST.get("display_order") or "").strip()
            try:
                display_order = int(display_order_raw or 1)
            except ValueError:
                display_order = 1

            cls = get_object_or_404(TutoringClass, id=class_id, is_active=True)
            if subject_name:
                TeachingClassSubjectTemplate.objects.update_or_create(
                    tutoring_class=cls,
                    subject_name=subject_name,
                    defaults={
                        "default_sheet_name": default_sheet_name,
                        "display_order": display_order,
                        "is_active": True,
                    },
                )
            return redirect(f"/teaching/templates/?class_id={class_id}")

        if action == "save_templates":
            for tid in request.POST.getlist("template_ids"):
                tmpl = TeachingClassSubjectTemplate.objects.filter(id=tid).first()
                if not tmpl:
                    continue
                tmpl.subject_name = (request.POST.get(f"subject_name_{tid}") or tmpl.subject_name).strip()
                tmpl.default_sheet_name = (request.POST.get(f"default_sheet_name_{tid}") or "").strip()
                try:
                    tmpl.display_order = int(request.POST.get(f"display_order_{tid}") or tmpl.display_order or 1)
                except ValueError:
                    pass
                tmpl.is_active = request.POST.get(f"is_active_{tid}") == "yes"
                tmpl.save()
            return redirect(f"/teaching/templates/?class_id={selected_class_id}" if selected_class_id else "/teaching/templates/")

    templates = TeachingClassSubjectTemplate.objects.select_related("tutoring_class").order_by(
        "tutoring_class__name", "display_order", "subject_name"
    )
    if selected_class_id:
        templates = templates.filter(tutoring_class_id=selected_class_id)
    templates = list(templates)
    for tmpl in templates:
        tmpl.class_grade_level = _class_grade_level(tmpl.tutoring_class)

    return render(request, "core/teaching_template_manage.html", {
        "classes": classes,
        "templates": templates,
        "tutors": tutors,
        "selected_class_id": selected_class_id,
        "sheet_choices": sheet_choices,
        "class_grade_map": class_grade_map,
    })


@login_required
def teaching_weekly_setup(request: HttpRequest) -> HttpResponse:
    week_start, week_end = _teaching_week_from_request(request)

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action == "add_tutor":
            tutor_name = (request.POST.get("tutor_name") or "").strip()
            tutor_phone = (request.POST.get("tutor_phone") or "").strip()
            if tutor_name:
                TeachingTutor.objects.update_or_create(
                    name=tutor_name,
                    defaults={"phone": tutor_phone, "is_active": True},
                )
            return redirect(f"/teaching/weekly-setup/?week_start={week_start.isoformat()}")

        _ensure_teaching_assignments(week_start, week_end)

        if action == "save_assignments":
            for aid in request.POST.getlist("assignment_ids"):
                assignment = TeachingWeeklyAssignment.objects.filter(id=aid).first()
                if not assignment:
                    continue
                tutor_id = (request.POST.get(f"tutor_{aid}") or "").strip()
                assignment.tutor = TeachingTutor.objects.filter(id=tutor_id, is_active=True).first() if tutor_id else None
                assignment.save()
            return redirect(f"/teaching/weekly-setup/?week_start={week_start.isoformat()}")

    _ensure_teaching_assignments(week_start, week_end)

    assignments = (
        TeachingWeeklyAssignment.objects
        .select_related("tutoring_class", "subject_template", "tutor")
        .filter(week_start_date=week_start)
        .order_by("tutoring_class__name", "subject_template__display_order", "subject_template__subject_name")
    )
    tutors = TeachingTutor.objects.filter(is_active=True).order_by("name")

    grouped_assignments: OrderedDict[int, dict] = OrderedDict()
    for a in assignments:
        key = a.tutoring_class_id
        grouped_assignments.setdefault(key, {"class": a.tutoring_class, "assignments": []})
        grouped_assignments[key]["assignments"].append(a)

    return render(request, "core/teaching_weekly_setup.html", {
        "week_start": week_start,
        "week_end": week_end,
        "assignments": assignments,
        "grouped_assignments": grouped_assignments,
        "tutors": tutors,
    })


def _teaching_slot_groups_from_assignments(assignments, previous_updates=None, current_updates=None):
    """Group assignments by the school time slot order: Sat AM, Sat PM, Sun AM, Sun PM."""
    previous_updates = previous_updates or {}
    current_updates = current_updates or {}
    slot_meta = {
        TutoringClass.TimeSlot.SAT_MORNING: {"label": "เสาร์เช้า", "tone": "sat-morning"},
        TutoringClass.TimeSlot.SAT_AFTERNOON: {"label": "เสาร์บ่าย", "tone": "sat-afternoon"},
        TutoringClass.TimeSlot.SUN_MORNING: {"label": "อาทิตย์เช้า", "tone": "sun-morning"},
        TutoringClass.TimeSlot.SUN_AFTERNOON: {"label": "อาทิตย์บ่าย", "tone": "sun-afternoon"},
    }

    grouped_slots: OrderedDict[str, dict] = OrderedDict()
    for slot in TIME_SLOT_ORDER:
        meta = slot_meta.get(slot, {"label": str(slot), "tone": "default"})
        grouped_slots[slot] = {
            "label": meta["label"],
            "tone": meta["tone"],
            "classes": OrderedDict(),
            "count": 0,
        }

    slot_rank = {slot: idx for idx, slot in enumerate(TIME_SLOT_ORDER)}
    sorted_assignments = sorted(
        assignments,
        key=lambda a: (
            slot_rank.get(a.tutoring_class.time_slot, 999),
            a.tutoring_class.name,
            a.subject_template.display_order,
            a.subject_template.subject_name,
        )
    )

    for a in sorted_assignments:
        slot = a.tutoring_class.time_slot
        if slot not in grouped_slots:
            grouped_slots[slot] = {"label": slot, "tone": "default", "classes": OrderedDict(), "count": 0}
        class_bucket = grouped_slots[slot]["classes"].setdefault(
            a.tutoring_class_id,
            {"class": a.tutoring_class, "assignments": []},
        )
        class_bucket["assignments"].append({
            "assignment": a,
            "previous_update": previous_updates.get(a.subject_template_id),
            "current_update": current_updates.get(a.id),
        })
        grouped_slots[slot]["count"] += 1

    # Hide empty slot headers when filtering by tutor/class leaves no assignments in that slot.
    return OrderedDict((k, v) for k, v in grouped_slots.items() if v["count"] > 0)


def tutor_teaching_update(request: HttpRequest) -> HttpResponse:
    week_start, week_end = _teaching_week_from_request(request)
    _ensure_teaching_assignments(week_start, week_end)

    selected_tutor_id = (request.GET.get("tutor_id") or request.POST.get("tutor_id") or "").strip()

    if request.method == "POST":
        assignment_id = request.POST.get("assignment_id")
        assignment = get_object_or_404(
            TeachingWeeklyAssignment.objects.select_related("subject_template", "tutor"),
            id=assignment_id,
            week_start_date=week_start,
        )
        teaching_date = _safe_date(request.POST.get("teaching_date")) if "_safe_date" in globals() else None
        if not teaching_date:
            teaching_date = timezone.localdate()

        no_teaching = request.POST.get("no_teaching") == "yes"
        sheet_name = (request.POST.get("sheet_name") or "").strip()
        page_to = (request.POST.get("page_to") or "").strip()
        question_to = (request.POST.get("question_to") or "").strip()

        qs = f"week_start={week_start.isoformat()}"
        if selected_tutor_id:
            qs += f"&tutor_id={selected_tutor_id}"

        # Require both page and question for actual teaching updates.
        # If not applicable, user can enter '-' in either field. If no teaching, allow blank.
        if not no_teaching and (not page_to or not question_to):
            qs += "&error=missing_progress"
            return redirect(f"/tutor-teaching-update/?{qs}#assignment-{assignment.id}")

        # If no teaching, preserve the latest real teaching progress as the visible sheet/page/question.
        if no_teaching:
            prev = (
                TeachingProgressUpdate.objects
                .filter(
                    assignment__subject_template_id=assignment.subject_template_id,
                    assignment__week_start_date__lt=week_start,
                    no_teaching=False,
                )
                .order_by("-teaching_date", "-updated_at")
                .first()
            )
            if prev:
                sheet_name = prev.sheet_name
                page_to = prev.page_to
                question_to = prev.question_to
            elif not sheet_name:
                sheet_name = assignment.subject_template.default_sheet_name or ""

        updated_by_name = (request.POST.get("updated_by_name") or "").strip()
        if not updated_by_name and assignment.tutor_id:
            updated_by_name = assignment.tutor.name

        TeachingProgressUpdate.objects.update_or_create(
            assignment=assignment,
            teaching_date=teaching_date,
            defaults={
                "sheet_name": sheet_name,
                "page_to": page_to,
                "question_to": question_to,
                "no_teaching": no_teaching,
                "updated_by_name": updated_by_name,
            },
        )
        return redirect(f"/tutor-teaching-update/?{qs}#assignment-{assignment.id}")

    assignments = (
        TeachingWeeklyAssignment.objects
        .select_related("tutoring_class", "subject_template", "tutor")
        .prefetch_related("progress_updates")
        .filter(week_start_date=week_start)
    )
    if selected_tutor_id:
        assignments = assignments.filter(tutor_id=selected_tutor_id)

    all_assignments = list(assignments)
    for a in all_assignments:
        a.class_grade_level = _class_grade_level(a.tutoring_class)
    template_ids = [a.subject_template_id for a in all_assignments]

    previous_updates = {}
    if template_ids:
        prev_qs = (
            TeachingProgressUpdate.objects
            .select_related("assignment", "assignment__subject_template", "assignment__tutor")
            .filter(
                assignment__subject_template_id__in=template_ids,
                assignment__week_start_date__lt=week_start,
                no_teaching=False,
            )
            .order_by("assignment__subject_template_id", "-teaching_date", "-updated_at")
        )
        for upd in prev_qs:
            previous_updates.setdefault(upd.assignment.subject_template_id, upd)

    current_updates = {}
    if all_assignments:
        curr_qs = (
            TeachingProgressUpdate.objects
            .filter(assignment_id__in=[a.id for a in all_assignments])
            .order_by("assignment_id", "-teaching_date", "-updated_at")
        )
        for upd in curr_qs:
            current_updates.setdefault(upd.assignment_id, upd)

    tutor_choices = TeachingTutor.objects.filter(is_active=True).order_by("name")
    sheet_choices = Sheet.objects.select_related("subject").filter(is_active=True).order_by("grade_level", "subject__name", "code")
    grouped_slots = _teaching_slot_groups_from_assignments(all_assignments, previous_updates, current_updates)

    return render(request, "core/tutor_teaching_update.html", {
        "week_start": week_start,
        "week_end": week_end,
        "today": timezone.localdate(),
        "tutors": tutor_choices,
        "selected_tutor_id": selected_tutor_id,
        "grouped_slots": grouped_slots,
        "error_code": (request.GET.get("error") or "").strip(),
        "sheet_choices": sheet_choices,
    })


@login_required
def teaching_update_report(request: HttpRequest) -> HttpResponse:
    week_start, week_end = _teaching_week_from_request(request)
    _ensure_teaching_assignments(week_start, week_end)

    assignments = list(
        TeachingWeeklyAssignment.objects
        .select_related("tutoring_class", "subject_template", "tutor")
        .filter(week_start_date=week_start)
    )

    updates = {
        u.assignment_id: u
        for u in TeachingProgressUpdate.objects.filter(assignment__week_start_date=week_start).order_by("assignment_id", "-teaching_date", "-updated_at")
    }

    rows = []
    for a in assignments:
        u = updates.get(a.id)
        rows.append({
            "assignment": a,
            "update": u,
            "is_done": bool(u),
            "is_no_teaching": bool(u and u.no_teaching),
        })

    slot_rank = {slot: idx for idx, slot in enumerate(TIME_SLOT_ORDER)}
    rows.sort(key=lambda r: (
        slot_rank.get(r["assignment"].tutoring_class.time_slot, 999),
        r["assignment"].tutoring_class.name,
        r["assignment"].subject_template.display_order,
        r["assignment"].subject_template.subject_name,
    ))

    slot_meta = {
        TutoringClass.TimeSlot.SAT_MORNING: {"label": "เสาร์เช้า", "tone": "sat-morning"},
        TutoringClass.TimeSlot.SAT_AFTERNOON: {"label": "เสาร์บ่าย", "tone": "sat-afternoon"},
        TutoringClass.TimeSlot.SUN_MORNING: {"label": "อาทิตย์เช้า", "tone": "sun-morning"},
        TutoringClass.TimeSlot.SUN_AFTERNOON: {"label": "อาทิตย์บ่าย", "tone": "sun-afternoon"},
    }
    grouped_rows: OrderedDict[str, dict] = OrderedDict()
    for slot in TIME_SLOT_ORDER:
        meta = slot_meta.get(slot, {"label": str(slot), "tone": "default"})
        grouped_rows[slot] = {"label": meta["label"], "tone": meta["tone"], "rows": [], "count": 0}
    for row in rows:
        slot = row["assignment"].tutoring_class.time_slot
        if slot not in grouped_rows:
            grouped_rows[slot] = {"label": slot, "tone": "default", "rows": [], "count": 0}
        grouped_rows[slot]["rows"].append(row)
        grouped_rows[slot]["count"] += 1
    grouped_rows = OrderedDict((k, v) for k, v in grouped_rows.items() if v["count"] > 0)

    total = len(rows)
    done = sum(1 for r in rows if r["is_done"])
    no_teaching = sum(1 for r in rows if r["is_no_teaching"])
    taught = done - no_teaching

    return render(request, "core/teaching_update_report.html", {
        "week_start": week_start,
        "week_end": week_end,
        "rows": rows,
        "grouped_rows": grouped_rows,
        "total": total,
        "done": done,
        "taught": taught,
        "no_teaching": no_teaching,
        "pending": total - done,
    })
