"""Revenue / cost / profit analysis per tutoring class.

Two layers:

* `suggest_*` — read real data (Attendance, Enrollment, SchoolExpense, payroll)
  to pre-fill a scenario's inputs. Only ever used to seed the form.
* `compute_scenario` — pure arithmetic over the saved inputs. No DB reads of
  actuals, so a scenario always reproduces the same numbers.

Cost model
----------
Revenue        = students x revenue/student/hr x hrs/session x sessions
Variable cost  = (teaching cost/hr x hrs/session x sessions) + other variable
Contribution   = Revenue - Variable cost          <- covers fixed cost
Allocated fix  = share of monthly fixed cost (see ALLOCATION below)
Net profit     = Contribution - Allocated fixed

Teaching cost is treated as variable-per-session rather than per-student: one
tutor is paid the same whether 6 or 12 students show up. That is what makes
each extra student almost pure contribution, and it is the single most
important lever in this business.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0")


def _d(value, default="0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _q(value: Decimal, places="0.01") -> Decimal:
    return _d(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def month_bounds(anchor: date) -> tuple[date, date]:
    start = anchor.replace(day=1)
    end = start.replace(day=monthrange(start.year, start.month)[1])
    return start, end


# ---------------------------------------------------------------- suggestions

def suggest_sessions_in_month(tutoring_class, start: date, end: date) -> Decimal:
    """How many times this class actually met, from attendance records.

    Falls back to counting calendar weeks when nothing was checked in yet
    (the business rule is one 4-hour session per week).
    """
    from .models import Attendance

    dates = (
        Attendance.objects
        .filter(
            enrollment__tutoring_class=tutoring_class,
            attendance_date__gte=start,
            attendance_date__lte=end,
        )
        .values_list("attendance_date", flat=True)
        .distinct()
    )
    count = len(set(dates))
    if count:
        return Decimal(count)
    # No attendance yet -> assume weekly.
    return Decimal((end - start).days // 7 + 1)


def suggest_student_count(tutoring_class, start: date, end: date) -> int:
    """How many distinct students the class actually had that month.

    Attendance is the truthful signal -- it reflects who was really in the room
    during the period. Enrollment records only say who is on the books *now*,
    which drifts as students join and leave. Falls back to active enrolments
    when the month has no attendance yet (e.g. modelling a future month).
    """
    from .models import Attendance, Enrollment

    attended = (
        Attendance.objects
        .filter(
            enrollment__tutoring_class=tutoring_class,
            attendance_date__gte=start,
            attendance_date__lte=end,
        )
        .values("student_id")
        .distinct()
        .count()
    )
    if attended:
        return attended

    return (
        Enrollment.objects
        .filter(tutoring_class=tutoring_class, is_active=True)
        .values("student_id")
        .distinct()
        .count()
    )


def suggest_revenue_per_student_hour(tutoring_class) -> Decimal:
    """Derive an hourly price from what students actually paid.

    net_price / sessions_total / hours_per_session, averaged over active
    enrollments. Falls back to the class list price, then to 0.
    """
    from .models import Enrollment

    hours = _d(tutoring_class.hours_per_session, "3")
    if hours <= 0:
        hours = Decimal("3")

    rows = list(
        Enrollment.objects
        .filter(tutoring_class=tutoring_class, is_active=True)
        .values_list("net_price", "sessions_total")
    )
    rates = [
        _d(price) / Decimal(sessions) / hours
        for price, sessions in rows
        if _d(price) > 0 and sessions
    ]
    if rates:
        return _q(sum(rates) / Decimal(len(rates)))

    price = _d(tutoring_class.course_price)
    if price > 0:
        return _q(price / Decimal("10") / hours)  # assume a 10-session package
    return ZERO


def suggest_teaching_cost_per_hour(start: date, end: date) -> Decimal:
    """Blended actual tutor rate for the month, from payroll entries."""
    from .models import TutorPayrollEntry

    rows = TutorPayrollEntry.objects.filter(work_date__gte=start, work_date__lte=end)
    total_fee = ZERO
    total_hours = ZERO
    for r in rows:
        total_fee += _d(r.teaching_fee)
        total_hours += _d(r.teaching_hours)
    if total_hours > 0:
        return _q(total_fee / total_hours)
    return Decimal("300")


def suggest_fixed_costs(start: date, end: date) -> list[dict]:
    """Non-payroll expenses for the month, grouped by category.

    Tutor payroll is excluded because it is already modelled as a variable
    per-session cost; counting it twice would understate every class.
    """
    from .models import SchoolExpense

    totals: dict[str, Decimal] = {}
    rows = (
        SchoolExpense.objects
        .select_related("category")
        .filter(expense_date__gte=start, expense_date__lte=end)
    )
    for r in rows:
        if r.category and r.category.is_tutor_payroll:
            continue
        key = r.category.name if r.category else "อื่น ๆ"
        totals[key] = totals.get(key, ZERO) + _d(r.amount)
    return [
        {"name": name, "amount": _q(amount)}
        for name, amount in sorted(totals.items(), key=lambda kv: -kv[1])
    ]


# ---------------------------------------------------------------- computation

@dataclass
class ClassResult:
    class_id: int
    name: str
    seats: int
    students: int
    sessions: Decimal
    hours_per_session: Decimal
    teaching_cost_per_hour: Decimal
    revenue_per_student_hour: Decimal
    other_variable_cost: Decimal

    total_hours: Decimal = ZERO
    student_hours: Decimal = ZERO
    revenue: Decimal = ZERO
    teaching_cost: Decimal = ZERO
    variable_cost: Decimal = ZERO
    contribution: Decimal = ZERO
    contribution_ratio: Decimal = ZERO
    contribution_per_student: Decimal = ZERO
    allocated_fixed: Decimal = ZERO
    net_profit: Decimal = ZERO
    net_margin: Decimal = ZERO

    # Decision metrics
    breakeven_students: Decimal = ZERO
    margin_of_safety: Decimal = ZERO
    utilization: Decimal = ZERO
    revenue_per_seat_hour: Decimal = ZERO
    profit_per_teaching_hour: Decimal = ZERO
    operating_leverage: Decimal = ZERO
    sensitivity: list = field(default_factory=list)
    flags: list = field(default_factory=list)


def _allocation_weights(rows: list[ClassResult], method: str) -> dict[int, Decimal]:
    """Share of fixed cost each class carries. Weights always sum to 1."""
    if method == "hours":
        raw = {r.class_id: r.total_hours for r in rows}
    elif method == "revenue":
        raw = {r.class_id: r.revenue for r in rows}
    elif method == "equal":
        raw = {r.class_id: Decimal("1") for r in rows}
    else:  # students (default)
        raw = {r.class_id: Decimal(r.students) for r in rows}

    total = sum(raw.values(), ZERO)
    if total <= 0:
        # Nothing to weight on -> split evenly so fixed cost is never dropped.
        n = Decimal(len(rows)) if rows else Decimal("1")
        return {r.class_id: Decimal("1") / n for r in rows}
    return {cid: (w / total) for cid, w in raw.items()}


def compute_scenario(scenario) -> dict:
    """Run the full analysis. Returns per-class rows plus portfolio totals."""
    inputs = list(
        scenario.class_inputs.select_related("tutoring_class").filter(is_included=True)
    )

    rows: list[ClassResult] = []
    for ci in inputs:
        cls = ci.tutoring_class
        sessions = _d(ci.sessions_per_month if ci.sessions_per_month is not None
                      else scenario.default_sessions_per_month)
        hours = _d(ci.hours_per_session if ci.hours_per_session is not None
                   else scenario.default_hours_per_session)
        cost_hr = _d(ci.teaching_cost_per_hour if ci.teaching_cost_per_hour is not None
                     else scenario.default_teaching_cost_per_hour)
        rev_hr = _d(ci.revenue_per_student_hour if ci.revenue_per_student_hour is not None
                    else scenario.default_revenue_per_student_hour)

        r = ClassResult(
            class_id=cls.id,
            name=cls.name,
            seats=int(cls.total_seats or 0),
            students=int(ci.student_count or 0),
            sessions=sessions,
            hours_per_session=hours,
            teaching_cost_per_hour=cost_hr,
            revenue_per_student_hour=rev_hr,
            other_variable_cost=_d(ci.other_variable_cost),
        )

        r.total_hours = sessions * hours
        r.student_hours = r.total_hours * Decimal(r.students)
        r.revenue = r.student_hours * rev_hr
        r.teaching_cost = r.total_hours * cost_hr
        r.variable_cost = r.teaching_cost + r.other_variable_cost
        r.contribution = r.revenue - r.variable_cost
        r.contribution_ratio = (r.contribution / r.revenue * 100) if r.revenue > 0 else ZERO
        r.contribution_per_student = (
            r.contribution / Decimal(r.students) if r.students else ZERO
        )
        rows.append(r)

    # Fixed cost allocation
    total_fixed = sum((_d(f.amount) for f in scenario.fixed_costs.all()), ZERO)
    weights = _allocation_weights(rows, scenario.allocation_method)

    for r in rows:
        r.allocated_fixed = _q(total_fixed * weights.get(r.class_id, ZERO))
        r.net_profit = r.contribution - r.allocated_fixed
        r.net_margin = (r.net_profit / r.revenue * 100) if r.revenue > 0 else ZERO

        # --- decision metrics -------------------------------------------------
        # Contribution from ONE student over the month; the marginal lever.
        per_student_contrib = r.total_hours * r.revenue_per_student_hour
        fixed_to_cover = r.variable_cost + r.allocated_fixed
        if per_student_contrib > 0:
            r.breakeven_students = fixed_to_cover / per_student_contrib
            if r.students > 0:
                r.margin_of_safety = (
                    (Decimal(r.students) - r.breakeven_students) / Decimal(r.students) * 100
                )
        r.utilization = (
            Decimal(r.students) / Decimal(r.seats) * 100 if r.seats else ZERO
        )
        # RevPASH: revenue per *available* seat-hour. Normalises classes of
        # different size and length so they can be ranked fairly.
        seat_hours = r.total_hours * Decimal(r.seats) if r.seats else ZERO
        r.revenue_per_seat_hour = (r.revenue / seat_hours) if seat_hours > 0 else ZERO
        r.profit_per_teaching_hour = (
            r.net_profit / r.total_hours if r.total_hours > 0 else ZERO
        )
        # How violently profit swings with enrolment. >3 means fragile.
        r.operating_leverage = (
            r.contribution / r.net_profit if r.net_profit != 0 else ZERO
        )

        # What-if: profit at -2..+3 students, holding everything else constant.
        r.sensitivity = []
        for delta in (-2, -1, 0, 1, 2, 3):
            n = r.students + delta
            if n < 0:
                continue
            rev = r.total_hours * Decimal(n) * r.revenue_per_student_hour
            profit = rev - r.variable_cost - r.allocated_fixed
            r.sensitivity.append({
                "delta": delta,
                "students": n,
                "profit": _q(profit),
                "is_current": delta == 0,
                "over_capacity": bool(r.seats and n > r.seats),
            })

        # --- advisory flags ---------------------------------------------------
        if r.contribution < 0:
            r.flags.append({
                "level": "danger",
                "text": "ขาดทุนตั้งแต่ระดับ contribution — ค่าสอนแพงกว่ารายได้ ควรขึ้นราคา ลดชั่วโมง หรือยุบห้อง",
            })
        elif r.net_profit < 0:
            r.flags.append({
                "level": "warn",
                "text": "contribution เป็นบวกแต่ยังไม่พอกลบ fixed cost — เพิ่มนักเรียนอีก "
                        f"{_q(max(r.breakeven_students - Decimal(r.students), ZERO), '0.1')} คนจะคุ้มทุน",
            })
        if r.seats and r.utilization < 50:
            r.flags.append({
                "level": "warn",
                "text": f"ที่นั่งว่างเยอะ (ใช้ไป {_q(r.utilization, '0.1')}%) — ต้นทุนครูเท่าเดิมไม่ว่าจะมีกี่คน "
                        "ทุกคนที่เพิ่มคือกำไรเกือบเต็ม",
            })
        if r.operating_leverage > 3 and r.net_profit > 0:
            r.flags.append({
                "level": "info",
                "text": f"operating leverage สูง ({_q(r.operating_leverage, '0.1')}x) — "
                        "กำไรอ่อนไหวมาก นักเรียนหายไม่กี่คนอาจพลิกเป็นขาดทุน",
            })

    rows.sort(key=lambda r: r.net_profit, reverse=True)

    # ---- portfolio totals ----
    t_rev = sum((r.revenue for r in rows), ZERO)
    t_var = sum((r.variable_cost for r in rows), ZERO)
    t_contrib = sum((r.contribution for r in rows), ZERO)
    t_profit = t_contrib - total_fixed
    t_hours = sum((r.total_hours for r in rows), ZERO)
    t_students = sum((r.students for r in rows), 0)
    t_seats = sum((r.seats for r in rows), 0)

    totals = {
        "revenue": _q(t_rev),
        "variable_cost": _q(t_var),
        "contribution": _q(t_contrib),
        "contribution_ratio": _q((t_contrib / t_rev * 100) if t_rev > 0 else ZERO),
        "fixed_cost": _q(total_fixed),
        "net_profit": _q(t_profit),
        "net_margin": _q((t_profit / t_rev * 100) if t_rev > 0 else ZERO),
        "teaching_hours": _q(t_hours),
        "students": t_students,
        "seats": t_seats,
        "utilization": _q((Decimal(t_students) / Decimal(t_seats) * 100) if t_seats else ZERO),
        "class_count": len(rows),
        # Whole-school break-even: how much revenue is needed to cover fixed cost
        # at the current contribution ratio.
        "breakeven_revenue": _q(
            (total_fixed / (t_contrib / t_rev)) if (t_rev > 0 and t_contrib > 0) else ZERO
        ),
        "revenue_per_student": _q(t_rev / Decimal(t_students)) if t_students else ZERO,
        "profit_per_student": _q(t_profit / Decimal(t_students)) if t_students else ZERO,
    }
    totals["margin_of_safety"] = _q(
        ((t_rev - totals["breakeven_revenue"]) / t_rev * 100)
        if (t_rev > 0 and totals["breakeven_revenue"] > 0) else ZERO
    )

    # Round per-class figures for display last, so the maths above stays exact.
    for r in rows:
        for f in (
            "revenue", "teaching_cost", "variable_cost", "contribution",
            "contribution_ratio", "contribution_per_student", "allocated_fixed",
            "net_profit", "net_margin", "breakeven_students", "margin_of_safety",
            "utilization", "revenue_per_seat_hour", "profit_per_teaching_hour",
            "operating_leverage", "total_hours",
        ):
            setattr(r, f, _q(getattr(r, f)))

    # Chart scales (max absolute value drives bar widths in the template).
    max_abs_profit = max([abs(r.net_profit) for r in rows], default=Decimal("1")) or Decimal("1")
    max_revenue = max([r.revenue for r in rows], default=Decimal("1")) or Decimal("1")
    for r in rows:
        r.bar_profit_pct = _q(abs(r.net_profit) / max_abs_profit * 100, "0.1")
        r.bar_revenue_pct = _q(r.revenue / max_revenue * 100, "0.1")

    return {
        "rows": rows,
        "totals": totals,
        "fixed_costs": list(scenario.fixed_costs.all()),
        "allocation_label": scenario.get_allocation_method_display(),
        "waterfall": _waterfall(totals),
        "insights": _insights(rows, totals),
    }


def _waterfall(totals: dict) -> list[dict]:
    """Revenue -> variable -> contribution -> fixed -> profit, as % bars."""
    revenue = totals["revenue"]
    if revenue <= 0:
        return []
    scale = lambda v: _q(abs(v) / revenue * 100, "0.1")  # noqa: E731
    return [
        {"label": "รายได้", "value": totals["revenue"], "pct": Decimal("100.0"), "kind": "rev"},
        {"label": "− ต้นทุนผันแปร (ค่าสอน ฯลฯ)", "value": totals["variable_cost"],
         "pct": scale(totals["variable_cost"]), "kind": "var"},
        {"label": "= Contribution Margin", "value": totals["contribution"],
         "pct": scale(totals["contribution"]), "kind": "contrib"},
        {"label": "− Fixed Cost", "value": totals["fixed_cost"],
         "pct": scale(totals["fixed_cost"]), "kind": "fixed"},
        {"label": "= กำไรสุทธิ", "value": totals["net_profit"],
         "pct": scale(totals["net_profit"]),
         "kind": "profit" if totals["net_profit"] >= 0 else "loss"},
    ]


def _insights(rows: list[ClassResult], totals: dict) -> list[dict]:
    """Plain-language takeaways, ordered most-actionable first."""
    out: list[dict] = []
    if not rows:
        return out

    losers = [r for r in rows if r.net_profit < 0]
    if losers:
        worst = min(losers, key=lambda r: r.net_profit)
        out.append({
            "level": "danger",
            "title": f"{len(losers)} ห้องขาดทุน",
            "text": f"หนักสุดคือ {worst.name} ขาดทุน {abs(worst.net_profit):,.0f} บาท/เดือน "
                    f"(ต้องมี {worst.breakeven_students:,.1f} คนถึงคุ้มทุน ตอนนี้มี {worst.students} คน)",
        })

    subsidisers = [r for r in rows if r.net_profit > 0]
    if subsidisers and losers:
        best = max(subsidisers, key=lambda r: r.net_profit)
        out.append({
            "level": "info",
            "title": "มีการอุ้มข้ามห้อง",
            "text": f"{best.name} ทำกำไร {best.net_profit:,.0f} บาท กำลังอุ้มห้องที่ขาดทุนอยู่ "
                    "ถ้าปิดห้องที่ขาดทุน fixed cost จะถูกปันมาที่ห้องที่เหลือแทน กำไรรวมอาจไม่เพิ่มตามที่คิด",
        })

    empty = [r for r in rows if r.seats and r.utilization < 60]
    if empty:
        gain = sum(
            ((Decimal(r.seats) - Decimal(r.students)) * r.total_hours * r.revenue_per_student_hour)
            for r in empty
        )
        out.append({
            "level": "success",
            "title": "โอกาสที่ใหญ่ที่สุดคือเก้าอี้ว่าง",
            "text": f"{len(empty)} ห้องยังใช้ที่นั่งไม่ถึง 60% ถ้าเติมเต็มทุกที่นั่ง "
                    f"จะได้รายได้เพิ่มอีกราว {gain:,.0f} บาท/เดือน โดยต้นทุนครูเท่าเดิม "
                    "(เกือบทั้งหมดจะกลายเป็นกำไร)",
        })

    if totals["contribution_ratio"] > 0:
        out.append({
            "level": "info",
            "title": "จุดคุ้มทุนของทั้งโรงเรียน",
            "text": f"ต้องมีรายได้ {totals['breakeven_revenue']:,.0f} บาท/เดือน ถึงจะคุ้ม fixed cost "
                    f"ตอนนี้ทำได้ {totals['revenue']:,.0f} บาท "
                    f"(ห่างจากจุดคุ้มทุน {totals['margin_of_safety']:,.1f}%)",
        })

    best_yield = max(rows, key=lambda r: r.revenue_per_seat_hour, default=None)
    if best_yield and best_yield.revenue_per_seat_hour > 0:
        out.append({
            "level": "info",
            "title": "ห้องที่ใช้เวลาคุ้มที่สุด",
            "text": f"{best_yield.name} ทำรายได้ {best_yield.revenue_per_seat_hour:,.0f} บาท "
                    "ต่อที่นั่งต่อชั่วโมง สูงสุดในบรรดาห้องทั้งหมด "
                    "ตัวเลขนี้เทียบห้องที่ขนาด/ชั่วโมงต่างกันได้อย่างเป็นธรรม ใช้เลือกว่าควรขยายห้องไหน",
        })

    return out
