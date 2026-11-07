"""Tutor pay overview: hours and money per tutor over a chosen period, plus
an audit of saved payroll entries against the current rate rules."""
from __future__ import annotations

import copy
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .models import TutorPayrollEntry

ZERO = Decimal("0")
MONEY_FIELDS = ("hourly_rate", "teaching_fee", "online_teaching_fee", "travel_fee", "total_amount", "net_amount")


def _parse(s):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def expected(entry: TutorPayrollEntry) -> TutorPayrollEntry:
    """What the entry's money would be if recalculated with today's rules."""
    c = copy.copy(entry)
    c.recalculate()
    return c


def audit(entry: TutorPayrollEntry) -> list[str]:
    """Human-readable problems with one saved entry (empty = fine)."""
    issues = []
    exp = expected(entry)
    hours = Decimal(str(entry.teaching_hours or 0))
    auto_rate = TutorPayrollEntry.calculate_hourly_rate(hours, entry.special_rate_325, entry.special_rate_350)
    if entry.hourly_rate_override is not None and hours > 0 and Decimal(str(entry.hourly_rate_override)) != auto_rate:
        msg = f"เรทกำหนดเอง {entry.hourly_rate_override:,.0f} แทนเรทอัตโนมัติ {auto_rate:,.0f}"
        if entry.special_rate_325 and auto_rate == Decimal("325"):
            msg += " (ติ๊ก 325 ไว้แต่ไม่ถูกใช้)"
        issues.append(msg)
    if entry.travel_fee_override is not None and hours > 0:
        auto_travel = TutorPayrollEntry.calculate_travel_fee(hours)
        if Decimal(str(entry.travel_fee_override)) != auto_travel:
            issues.append(f"ค่าเดินทางกำหนดเอง {entry.travel_fee_override:,.0f} แทน {auto_travel:,.0f}")
    stale = [f for f in MONEY_FIELDS if Decimal(str(getattr(entry, f) or 0)) != Decimal(str(getattr(exp, f) or 0))]
    if stale:
        issues.append(f"ยอดที่บันทึกไว้ {entry.total_amount:,.2f} ไม่ตรงกับคำนวณใหม่ {exp.total_amount:,.2f}")
    return issues


def _weeks(start: date, end: date) -> list[date]:
    d = start - timedelta(days=start.weekday())
    out = []
    while d <= end:
        out.append(d)
        d += timedelta(days=7)
    return out


@login_required
def tutor_pay_page(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        return HttpResponse(status=403)

    if request.method == "POST":
        action, pk = request.POST.get("action"), request.POST.get("id")
        qs = TutorPayrollEntry.objects.filter(pk=pk) if pk else TutorPayrollEntry.objects.none()
        for e in qs:
            if action == "clear_override":
                e.hourly_rate_override = None
                e.travel_fee_override = None
            e.save()  # save() recalculates every amount
        if action == "recalc_all":
            for e in TutorPayrollEntry.objects.filter(pk__in=request.POST.getlist("ids")):
                if audit(e):
                    e.save()
        return redirect(request.get_full_path())

    latest = TutorPayrollEntry.objects.order_by("-work_date").values_list("work_date", flat=True).first() or date.today()
    mode = request.GET.get("mode") or "month"
    d_from, d_to = _parse(request.GET.get("from")), _parse(request.GET.get("to"))
    picked_weeks = sorted({w for w in (_parse(x) for x in request.GET.getlist("week")) if w})
    if mode == "range" and d_from and d_to:
        start, end = min(d_from, d_to), max(d_from, d_to)
    elif mode == "weeks" and picked_weeks:
        start, end = picked_weeks[0], picked_weeks[-1] + timedelta(days=6)
    else:
        mode = "month"
        month = _parse((request.GET.get("month") or "") + "-01") or latest.replace(day=1)
        start, end = month, month.replace(day=monthrange(month.year, month.month)[1])

    entries = list(
        TutorPayrollEntry.objects.filter(work_date__range=(start, end)).select_related("tutor").order_by("work_date", "tutor__name")
    )
    if mode == "weeks":
        wanted = set(picked_weeks)
        entries = [e for e in entries if e.work_date - timedelta(days=e.work_date.weekday()) in wanted]

    tutors: dict[int, dict] = {}
    totals = {k: ZERO for k in ("onsite_hours", "online_hours", "hours", "onsite_fee", "online_fee", "travel_fee", "idle_fee", "total", "wht", "net")}
    problems = []
    for e in entries:
        e.issues = audit(e)
        if e.issues:
            e.exp_total = expected(e).total_amount
            auto = copy.copy(e)
            auto.hourly_rate_override = auto.travel_fee_override = None
            auto.recalculate()
            e.auto_total = auto.total_amount
            problems.append(e)
        t = tutors.setdefault(e.tutor_id, {"tutor": e.tutor, "entries": [], "days": 0, **{k: ZERO for k in totals}})
        vals = {
            "onsite_hours": e.teaching_hours or ZERO, "online_hours": e.online_teaching_hours or ZERO,
            "onsite_fee": e.teaching_fee or ZERO, "online_fee": e.online_teaching_fee or ZERO,
            "travel_fee": e.travel_fee or ZERO, "idle_fee": e.idle_fee or ZERO,
            "total": e.total_amount or ZERO, "wht": e.withholding_amount or ZERO, "net": e.net_amount or ZERO,
        }
        vals["hours"] = vals["onsite_hours"] + vals["online_hours"]
        for k, v in vals.items():
            t[k] += v
            totals[k] += v
        t["entries"].append(e)
        t["days"] += 1
    rows = sorted(tutors.values(), key=lambda r: -r["total"])
    for r in rows:
        r["avg_rate"] = (r["onsite_fee"] + r["online_fee"]) / r["hours"] if r["hours"] else ZERO
        r["issue_count"] = sum(1 for e in r["entries"] if e.issues)

    recent = list(TutorPayrollEntry.objects.select_related("tutor").order_by("-updated_at")[:12])
    for e in recent:
        e.issues = audit(e)
    week_choices = [
        {"start": w, "end": w + timedelta(days=6), "on": w in picked_weeks}
        for w in reversed(_weeks(latest - timedelta(days=7 * 15), latest))
    ]
    return render(request, "core/tutor_pay.html", {
        "rows": rows, "totals": totals, "start": start, "end": end, "mode": mode,
        "month_value": start.strftime("%Y-%m"), "latest": latest, "recent": recent,
        "problems": problems, "week_choices": week_choices, "entry_count": len(entries),
    })
