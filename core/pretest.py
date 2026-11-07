"""📝 Pre-test applications the school files on students' behalf.

One page (/pretest-applications/). Rows come from the Google Form export
(.xlsx) uploaded on the page -- the file holds children's national IDs, so it
is never committed to the repo or kept on disk. Re-uploading is safe: rows are
keyed by national ID, so only new students are added.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from io import BytesIO

import openpyxl
import pypdfium2
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .models import Enrollment, PretestApplication, PretestRound, PretestStatusColor, Student

FEE = 200
NOT_STARTED = "not_started"
DEFAULT_STATUS_COLORS = {NOT_STARTED: "#94a3b8", "is_printed": "#6d28d9", "is_signed": "#6d28d9",
                         "is_paid": "#6d28d9", "is_filed": "#6d28d9", "is_returned": "#15803d"}
STEPS = [
    ("is_printed", "ปรินท์แล้ว"),
    ("is_signed", "ส่งเซ็นแล้ว"),
    ("is_paid", "รับเงินแล้ว"),
    ("is_filed", "ยื่นแล้ว"),
    ("is_returned", "ส่งกลับแล้ว"),
]
STEP_ICONS = {"is_printed": "🖨️", "is_signed": "✍️", "is_paid": "💰", "is_filed": "🏫", "is_returned": "📨"}
# (button, full name, colour, icon) -- same names and colours as the teaching schedule's rooms
ROOMS = [
    ("ทุเรียน", "ห้องทุเรียนหมอนทอง", "#f6e88a", "🍈"),
    ("มะม่วง", "ห้องมะม่วงเขียวเสวย", "#c6e2a8", "🥭"),
    ("แตงโม", "ห้องแตงโมจินตหรา", "#f5bcc7", "🍉"),
    ("มังคุด", "ห้องมังคุดคัด", "#dfc6ea", "🍇"),
    ("มะพร้าว", "ห้องมะพร้าว", "#cbbfae", "🥥"),
]
TEXT_FIELDS = {"nickname": 100, "first_name": 150, "last_name": 150, "phone": 20, "exam_number": 50}
_PREFIX = re.compile(r"^(เด็กหญิง|เด็กชาย|ด\.?\s?ญ\.?|ด\.?\s?ช\.?|นางสาว|นาย)\s*")


def _can_use(user) -> bool:
    from .views import _is_tool_owner
    return _is_tool_owner(user)  # sub-admins must not see national IDs


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value if value is not None else ""))


def valid_national_id(value: str) -> bool:
    if not re.fullmatch(r"\d{13}", value or ""):
        return False
    return (11 - sum(int(value[i]) * (13 - i) for i in range(12)) % 11) % 10 == int(value[12])


def split_name(raw) -> tuple[str, str]:
    """'ด.ญ.ธัญญลักษณ์ วรเวทวุฒิคุณ' -> ('ธัญญลักษณ์', 'วรเวทวุฒิคุณ')."""
    parts = _PREFIX.sub("", str(raw or "").strip()).split(None, 1)
    return (parts[0] if parts else "", parts[1].strip() if len(parts) > 1 else "")


def clean_nickname(raw) -> str:
    """'น้องบัว (ป.5)' / 'น้องคุน ป5/เสาร์บ่าย' -> 'บัว' / 'คุน'."""
    s = re.sub(r"\(.*?\)", "", str(raw or "")).strip()
    s = re.sub(r"\s*ป\.?\s?\d.*$", "", s).strip()
    return re.sub(r"^น้อง\s*", "", s).strip()


def _nick_key(value) -> str:
    return clean_nickname(value).replace(" ", "")


def find_student(app, students) -> Student | None:
    """Link only when the first name AND something else agree: first names
    repeat (two applicants here are both ธนภัทร), and siblings share a phone."""
    nick, phone = _nick_key(app.nickname), _digits(app.phone)
    scored = []
    for s in students:
        first, last = split_name(s.full_name)
        same_nick = bool(nick) and _nick_key(s.nickname) == nick
        same_phone = bool(phone) and _digits(s.parent_phone) == phone
        if first == app.first_name:
            hits = same_nick + same_phone + bool(app.last_name and last == app.last_name)
            if hits or not s.nickname:
                scored.append(s)
        elif same_nick and same_phone:
            scored.append(s)
    return scored[0] if len(scored) == 1 else None


def _column(headers, *keywords):
    for i, h in enumerate(headers):
        if any(k in str(h or "") for k in keywords):
            return i
    return None


def import_rows(rows) -> dict:
    """rows[0] is the header. Existing national IDs are left untouched."""
    rows = list(rows)
    headers = rows[0] if rows else []
    c_nick = _column(headers, "ชื่อเล่น")
    c_first = _column(headers, "ชื่อจริง")
    c_id = _column(headers, "บัตรประชาชน")
    c_phone = _column(headers, "เบอร์มือถือ")
    c_time = _column(headers, "Timestamp")
    if None in (c_nick, c_first, c_id, c_phone):
        raise ValueError("ไฟล์นี้ไม่มีคอลัมน์ ชื่อเล่น / ชื่อจริง / บัตรประชาชน / เบอร์มือถือ")
    existing = set(PretestApplication.objects.values_list("national_id", flat=True))
    students = list(Student.objects.all())
    out = {"added": 0, "duplicate": 0, "skipped": 0, "linked": 0}
    for r in rows[1:]:
        nid = _digits(r[c_id])
        if not r[c_first] and not nid:
            continue
        if len(nid) != 13:
            out["skipped"] += 1
            continue
        if nid in existing:
            out["duplicate"] += 1
            continue
        first, last = split_name(r[c_first])
        when = r[c_time] if c_time is not None else None
        when = timezone.make_aware(when) if isinstance(when, datetime) and timezone.is_naive(when) else None
        app = PretestApplication(nickname=clean_nickname(r[c_nick])[:100], first_name=first[:150], last_name=last[:150],
                                 national_id=nid, phone=_digits(r[c_phone])[:20], submitted_at=when)
        app.student = find_student(app, students)
        app.save()
        existing.add(nid)
        out["added"] += 1
        out["linked"] += 1 if app.student_id else 0
    return out


def import_forms_pdf(data: bytes) -> dict:
    """Split the school's combined PDF (one form per page) and attach each page
    to the application with the same national ID. Re-uploading replaces forms."""
    pdf = pypdfium2.PdfDocument(data)
    by_id = {a.national_id: a for a in PretestApplication.objects.defer("application_pdf")}
    out = {"pages": len(pdf), "matched": 0, "unmatched": []}
    for i in range(len(pdf)):
        text = pdf[i].get_textpage().get_text_range()
        ids = {_digits(x) for x in re.findall(r"\d(?:[ \-]*\d){12}", text)}
        ids = {x for x in ids if valid_national_id(x)}
        m = re.search(r"SSP\d*-\d+", text)
        no = m.group() if m else ""
        app = by_id.get(next(iter(ids))) if len(ids) == 1 else None
        if not app:
            out["unmatched"].append(no or f"หน้า {i + 1}")
            continue
        one = pypdfium2.PdfDocument.new()
        one.import_pages(pdf, [i])
        buf = BytesIO()
        one.save(buf)
        one.close()
        app.application_pdf = buf.getvalue()
        app.application_no = no[:30]
        app.save(update_fields=["application_pdf", "application_no", "updated_at"])
        out["matched"] += 1
    pdf.close()
    return out


def _classes_by_student(student_ids) -> dict:
    """{student_id: {class_id: name}} -- current classes, or the latest one for
    a student with no active enrollment."""
    out: dict = {}
    latest: dict = {}
    for e in Enrollment.objects.filter(student_id__in=student_ids).select_related("tutoring_class").order_by("-created_at"):
        latest.setdefault(e.student_id, {e.tutoring_class_id: e.tutoring_class.name})
        if e.is_active:
            out.setdefault(e.student_id, {})[e.tutoring_class_id] = e.tutoring_class.name
    return {**latest, **out}


def _student_label(s: Student) -> str:
    return f"{s.nickname or '-'} | {s.full_name or '-'} | {s.student_code or '-'}"


@login_required
def pretest_page(request: HttpRequest) -> HttpResponse:
    if not _can_use(request.user):
        return HttpResponse(status=403)
    if request.method == "POST" and request.FILES.get("pdf"):
        try:
            r = import_forms_pdf(request.FILES["pdf"].read())
            messages.success(request, f"แยกใบสมัคร {r['pages']} หน้า · จับคู่ได้ {r['matched']} ใบ" + (f" · จับคู่ไม่ได้: {', '.join(r['unmatched'])}" if r["unmatched"] else ""))
        except Exception as e:  # not a readable PDF
            messages.error(request, f"นำเข้า PDF ไม่สำเร็จ: {e}")
        return redirect("core:pretest_applications")
    if request.method == "POST":
        try:
            sheet = openpyxl.load_workbook(request.FILES["file"], read_only=True, data_only=True).worksheets[0]
            r = import_rows(sheet.iter_rows(values_only=True))
            messages.success(request, f"นำเข้าใหม่ {r['added']} คน (ผูกกับนักเรียนอัตโนมัติ {r['linked']}) · ข้ามรายการซ้ำ {r['duplicate']} · เลขบัตรไม่ครบ {r['skipped']}")
        except Exception as e:  # not a readable .xlsx, or the wrong sheet
            messages.error(request, f"นำเข้าไม่สำเร็จ: {e}")
        return redirect("core:pretest_applications")
    apps = list(PretestApplication.objects.select_related("student").defer("application_pdf"))
    colors = {**DEFAULT_STATUS_COLORS, **dict(PretestStatusColor.objects.values_list("status", "color"))}
    rounds = list(PretestRound.objects.all())
    for r in rounds:
        r.count = sum(1 for a in apps if a.round_id == r.id)
    classes = _classes_by_student({a.student_id for a in apps if a.student_id})
    for a in apps:
        mine = classes.get(a.student_id, {})
        a.class_ids = ",".join(str(i) for i in mine)
        a.class_names = ", ".join(sorted(mine.values()))
        a.id_ok = valid_national_id(a.national_id)
        a.phone_ok = len(_digits(a.phone)) == 10
        a.steps = [(f, label, getattr(a, f), STEP_ICONS[f]) for f, label in STEPS]
        a.done_count = sum(1 for f, _ in STEPS if getattr(a, f))
    return render(request, "core/pretest_applications.html", {
        "apps": apps,
        "fee": FEE,
        "paid_total": sum(1 for a in apps if a.is_paid) * FEE,
        "unlinked": sum(1 for a in apps if not a.student_id and not a.is_external),
        "external": sum(1 for a in apps if a.is_external),
        "rooms": ROOMS,
        "rounds": rounds,
        "status_colors": colors,
        "status_color_rows": [{"key": k, "label": label, "color": colors[k]} for k, label in [(NOT_STARTED, "ยังไม่เริ่ม"), *STEPS]],
        "no_round": sum(1 for a in apps if not a.round_id),
        "class_options": sorted(
            ({"id": i, "name": n, "count": sum(1 for a in apps if i in classes.get(a.student_id, {}))}
             for i, n in {i: n for m in classes.values() for i, n in m.items()}.items()),
            key=lambda c: c["name"],
        ),
        "no_class": sum(1 for a in apps if a.student_id not in classes),
        "no_form": sum(1 for a in apps if not a.application_no),
        "step_stats": [{"field": f, "label": label, "icon": STEP_ICONS[f], "count": sum(1 for a in apps if getattr(a, f))} for f, label in STEPS],
        "student_options": [{"id": s.id, "label": _student_label(s)} for s in Student.objects.order_by("-is_active", "nickname")],
    })


@login_required
def pretest_form_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    if not _can_use(request.user):
        return HttpResponse(status=403)
    app = get_object_or_404(PretestApplication, pk=pk, application_pdf__isnull=False)
    resp = HttpResponse(bytes(app.application_pdf), content_type="application/pdf")
    resp["Cache-Control"] = "private, no-store"
    return resp


def _round_action(action: str, v: dict) -> JsonResponse:
    if action == "bulk_round":
        round_id = v.get("round") or None
        if round_id and not PretestRound.objects.filter(id=round_id).exists():
            return JsonResponse({"ok": False, "error": "ไม่พบรอบนี้"}, status=400)
        done = PretestApplication.objects.filter(id__in=[int(i) for i in v.get("ids") or []]).update(round_id=round_id)
        return JsonResponse({"ok": True, "updated": done})
    existing = PretestRound.objects.filter(id=v.get("id")).first() if v.get("id") else None
    if action == "round_delete":
        if existing:
            existing.delete()  # its children go back to "no round"
        return JsonResponse({"ok": True})
    name = str(v.get("name") or "").strip()[:50]
    try:
        when = parse_date(str(v.get("filing_date") or ""))
    except ValueError:
        when = None
    if not name or not when:
        return JsonResponse({"ok": False, "error": "กรุณากรอกชื่อรอบและวันที่ยื่น"}, status=400)
    round_ = existing or PretestRound()
    round_.name, round_.filing_date = name, when
    round_.save()
    return JsonResponse({"ok": True})


def _add_application(v: dict) -> JsonResponse:
    """Manual entry; without a linked student the applicant counts as external."""
    nid = _digits(v.get("national_id"))
    first = str(v.get("first_name") or "").strip()
    if not first:
        return JsonResponse({"ok": False, "error": "กรุณากรอกชื่อจริง"}, status=400)
    if len(nid) != 13:
        return JsonResponse({"ok": False, "error": "เลขบัตรต้องมี 13 หลัก"}, status=400)
    if PretestApplication.objects.filter(national_id=nid).exists():
        return JsonResponse({"ok": False, "error": "เลขบัตรนี้มีใบสมัครแล้ว (1 คนยื่นได้ 1 ใบ)"}, status=400)
    student = Student.objects.filter(id=v["student"]).first() if v.get("student") else None
    PretestApplication.objects.create(
        nickname=str(v.get("nickname") or "").strip()[:100], first_name=first[:150],
        last_name=str(v.get("last_name") or "").strip()[:150], national_id=nid,
        phone=_digits(v.get("phone"))[:20], student=student, is_external=student is None,
        submitted_at=timezone.now(),
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
def pretest_api(request: HttpRequest) -> JsonResponse:
    if not _can_use(request.user):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    try:
        p = json.loads(request.body or "{}")
        if p.get("field") == "add":
            return _add_application(p.get("value") or {})
        if p.get("field") == "status_color":
            v = p.get("value") or {}
            if v.get("status") not in DEFAULT_STATUS_COLORS or not re.fullmatch(r"#[0-9a-fA-F]{6}", str(v.get("color"))):
                return JsonResponse({"ok": False, "error": "สีไม่ถูกต้อง"}, status=400)
            PretestStatusColor.objects.update_or_create(status=v["status"], defaults={"color": v["color"]})
            return JsonResponse({"ok": True})
        if p.get("field") in ("round_save", "round_delete", "bulk_round"):
            return _round_action(p.get("field"), p.get("value") or {})
        app = PretestApplication.objects.defer("application_pdf").get(id=int(p.get("id")))
    except (ValueError, TypeError, PretestApplication.DoesNotExist):
        return JsonResponse({"ok": False, "error": "ไม่พบรายการ"}, status=404)
    field, value = p.get("field"), p.get("value")
    if field == "delete":
        app.delete()
        return JsonResponse({"ok": True})
    if field in dict(STEPS):
        setattr(app, field, bool(value))
    elif field in TEXT_FIELDS:
        setattr(app, field, str(value or "").strip()[:TEXT_FIELDS[field]])
    elif field == "national_id":
        nid = _digits(value)
        if len(nid) != 13:
            return JsonResponse({"ok": False, "error": "เลขบัตรต้องมี 13 หลัก"}, status=400)
        if PretestApplication.objects.filter(national_id=nid).exclude(id=app.id).exists():
            return JsonResponse({"ok": False, "error": "เลขบัตรนี้มีใบสมัครแล้ว (1 คนยื่นได้ 1 ใบ)"}, status=400)
        app.national_id = nid
    elif field == "student":
        if value and not Student.objects.filter(id=value).exists():
            return JsonResponse({"ok": False, "error": "ไม่พบนักเรียน"}, status=400)
        app.student_id = value or None
        if value:
            app.is_external = False
    elif field == "round":
        if value and not PretestRound.objects.filter(id=value).exists():
            return JsonResponse({"ok": False, "error": "ไม่พบรอบนี้"}, status=400)
        app.round_id = value or None
    elif field == "is_external":
        app.is_external = bool(value)
        if value:
            app.student = None
    else:
        return JsonResponse({"ok": False, "error": "ไม่รู้จักช่องนี้"}, status=400)
    app.save()
    return JsonResponse({"ok": True, "id_ok": valid_national_id(app.national_id), "phone_ok": len(_digits(app.phone)) == 10})
