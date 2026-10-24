"""📄 Official documents for tutors: weekly payslip and the 50 ทวิ
withholding-tax certificate, built from TutorPayrollEntry rows."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from .analytics import school_week_start
from .models import DocumentIssuer, Tutor, TutorPayrollEntry

ZERO = Decimal("0")
_TH_MONTHS = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
              "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
_TH_MONTHS_ABBR = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
_DIG = ["", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]
_POS = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน"]


def _th_int(n: int) -> str:
    if n == 0:
        return ""
    if n >= 1_000_000:
        return _th_int(n // 1_000_000) + "ล้าน" + _th_int(n % 1_000_000)
    s, digits = "", str(n)
    L = len(digits)
    for i, ch in enumerate(digits):
        d, pos = int(ch), L - i - 1
        if d == 0:
            continue
        if pos == 1 and d == 1:
            s += "สิบ"
        elif pos == 1 and d == 2:
            s += "ยี่สิบ"
        elif pos == 0 and d == 1 and L > 1:
            s += "เอ็ด"
        else:
            s += _DIG[d] + _POS[pos]
    return s


def baht_text(amount) -> str:
    """Decimal('1234.50') -> 'หนึ่งพันสองร้อยสามสิบสี่บาทห้าสิบสตางค์'."""
    amount = Decimal(str(amount or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    baht, satang = int(amount), int((amount - int(amount)) * 100)
    if baht == 0 and satang == 0:
        return "ศูนย์บาทถ้วน"
    out = (_th_int(baht) + "บาท") if baht else ""
    return out + (_th_int(satang) + "สตางค์" if satang else "ถ้วน")


def th_date(d: date) -> str:
    return f"{d.day} {_TH_MONTHS[d.month]} {d.year + 543}"


def th_date_short(d: date) -> str:
    return f"{d.day} {_TH_MONTHS_ABBR[d.month]} {(d.year + 543) % 100:02d}"


def _issuer() -> DocumentIssuer:
    return DocumentIssuer.objects.order_by("id").first() or DocumentIssuer.objects.create()


def _range_from_request(request) -> tuple[date, date]:
    start = parse_date(request.GET.get("start") or "")
    end = parse_date(request.GET.get("end") or "")
    if not start:
        start = school_week_start(parse_date(request.GET.get("week") or "") or timezone.localdate())
    if not end:
        end = start + timedelta(days=6)
    return start, max(start, end)


def _n(d) -> str:
    """600.00 -> '600', 2.50 -> '2.5' (never scientific notation)."""
    d = Decimal(str(d or 0))
    return f"{d:,.0f}" if d == d.to_integral_value() else f"{d.normalize():,f}"


def _entry_lines(e: TutorPayrollEntry) -> list[dict]:
    lines = []
    if e.teaching_hours:
        lines.append({"label": f"ค่าสอน onsite {_n(e.teaching_hours)} ชม. × {_n(e.hourly_rate)}", "amount": e.teaching_fee})
    if e.online_teaching_hours:
        lines.append({"label": f"ค่าสอนออนไลน์ {_n(e.online_teaching_hours)} ชม. × {_n(e.online_hourly_rate)}", "amount": e.online_teaching_fee})
    if e.travel_fee:
        lines.append({"label": "ค่าเดินทาง", "amount": e.travel_fee})
    if e.idle_fee:
        lines.append({"label": "ค่านั่งว่าง / อื่น ๆ", "amount": e.idle_fee})
    return lines


@login_required
def official_docs_home(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        return HttpResponse(status=403)
    issuer = _issuer()
    if request.method == "POST":
        act = request.POST.get("action")
        if act == "issuer":
            for f in ("name", "tax_id", "address", "signer_name", "signer_position"):
                setattr(issuer, f, (request.POST.get(f) or "").strip()[:400])
            issuer.save()
            return redirect(f"{reverse('core:official_docs')}?saved=issuer")
        if act == "tutor":
            t = get_object_or_404(Tutor, id=request.POST.get("tutor_id"))
            t.first_name = (request.POST.get("first_name") or "").strip()[:120]
            t.last_name = (request.POST.get("last_name") or "").strip()[:120]
            t.national_id = "".join(ch for ch in (request.POST.get("national_id") or "") if ch.isdigit())[:13]
            t.address = (request.POST.get("address") or "").strip()[:400]
            t.default_withhold_3 = request.POST.get("default_withhold_3") == "on"
            t.save()
            return redirect(f"{reverse('core:official_docs')}?saved=tutor#tutor-{t.id}")

    week = school_week_start(timezone.localdate())
    recent_weeks = [week - timedelta(weeks=i) for i in range(10)]
    return render(request, "core/official_docs.html", {
        "issuer": issuer,
        "tutors": Tutor.objects.filter(is_active=True).order_by("name"),
        "weeks": [{"value": w.isoformat(), "label": f"{th_date_short(w)} – {th_date_short(w + timedelta(days=6))}"} for w in recent_weeks],
        "saved": request.GET.get("saved") or "",
    })


@login_required
def official_doc_payslip(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        return HttpResponse(status=403)
    tutor = get_object_or_404(Tutor, id=request.GET.get("tutor"))
    start, end = _range_from_request(request)
    entries = list(TutorPayrollEntry.objects.filter(tutor=tutor, work_date__range=(start, end)).order_by("work_date"))
    days = [{"date": e.work_date, "label": th_date_short(e.work_date), "lines": _entry_lines(e),
             "total": e.total_amount, "wht": e.withholding_amount, "net": e.net_amount} for e in entries]
    gross = sum((e.total_amount for e in entries), ZERO)
    wht = sum((e.withholding_amount for e in entries), ZERO)
    return render(request, "core/doc_payslip.html", {
        "issuer": _issuer(), "tutor": tutor, "days": days,
        "start": start, "end": end, "period_label": f"{th_date(start)} – {th_date(end)}",
        "gross": gross, "wht": wht, "net": gross - wht, "net_text": baht_text(gross - wht),
        "issued_label": th_date(timezone.localdate()),
    })


@login_required
def official_doc_wht50(request: HttpRequest) -> HttpResponse:
    """หนังสือรับรองการหักภาษี ณ ที่จ่าย ตามมาตรา 50 ทวิ -- only the
    payments that actually had 3% withheld are certified."""
    if not request.user.is_staff:
        return HttpResponse(status=403)
    tutor = get_object_or_404(Tutor, id=request.GET.get("tutor"))
    start, end = _range_from_request(request)
    entries = list(TutorPayrollEntry.objects.filter(tutor=tutor, work_date__range=(start, end), withholding_3=True))
    paid = sum((e.total_amount for e in entries), ZERO)
    tax = sum((e.withholding_amount for e in entries), ZERO)
    issue = parse_date(request.GET.get("issued") or "") or timezone.localdate()
    copy_no = "2" if request.GET.get("copy") == "2" else "1"
    issuer = _issuer()

    def boxes(tax_id: str) -> list[dict]:
        # 13 boxes grouped like the official form: 1-4-5-2-1
        d = "".join(ch for ch in (tax_id or "") if ch.isdigit())[:13].ljust(13)
        return [{"c": ch, "gap": i in (1, 5, 10, 12)} for i, ch in enumerate(d)]

    return render(request, "core/doc_wht50.html", {
        "issuer": issuer, "tutor": tutor, "entries_count": len(entries),
        "issuer_id_boxes": boxes(issuer.tax_id), "tutor_id_boxes": boxes(tutor.national_id),
        "paid": paid, "tax": tax, "tax_text": baht_text(tax),
        "pay_date_label": (th_date(end) if start == end else f"{th_date_short(start)} – {th_date_short(end)}"),
        "issued_label": th_date(issue), "copy_no": copy_no,
        "book_no": request.GET.get("book") or "", "doc_no": request.GET.get("no") or "",
        "seq_no": request.GET.get("seq") or "",
        "start": start, "end": end,
    })
