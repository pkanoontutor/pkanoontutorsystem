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

# Business rule: one attended session is four teaching hours. This is what
# converts a package price into an hourly rate, so it must stay in sync with
# how packages are actually sold.
SESSION_HOURS = Decimal("4")


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


# ------------------------------------------------- per-student hourly rates

def build_rate_timeline(student_ids=None) -> dict[int, list[tuple[date, Decimal]]]:
    """Each student's hourly rate history, derived from issued receipts.

    A receipt grants N sessions for a net amount, and one session is
    SESSION_HOURS hours, so:

        rate = net_amount / (sessions_granted * SESSION_HOURS)

    e.g. 3,990 THB for 10 sessions -> 3,990 / 40 = 99.75 THB/hour.

    That rate is locked in at purchase. A student who renews later at a
    different price gets a second entry, so revenue earned before the renewal
    is still valued at the old rate. Returns {student_id: [(date, rate), ...]}
    sorted by date.
    """
    from .models import CoursePayment

    qs = (
        CoursePayment.objects
        .filter(status=CoursePayment.ReceiptStatus.ISSUED, sessions_granted__gt=0)
        .values_list("student_id", "payment_date", "net_amount", "sessions_granted")
    )
    if student_ids is not None:
        qs = qs.filter(student_id__in=list(student_ids))

    timeline: dict[int, list[tuple[date, Decimal]]] = {}
    for student_id, pay_date, net_amount, sessions in qs:
        if not student_id or not sessions:
            continue
        amount = _d(net_amount)
        if amount <= 0:
            continue
        rate = amount / (Decimal(sessions) * SESSION_HOURS)
        timeline.setdefault(student_id, []).append((pay_date, rate))

    for rows in timeline.values():
        rows.sort(key=lambda r: r[0])
    return timeline


def rate_on(timeline: dict, student_id: int, on_date: date) -> Decimal | None:
    """The rate the student was paying as of `on_date`.

    Uses the most recent receipt on or before that date; if the attendance
    predates every receipt (back-dated data), falls back to the earliest one
    rather than dropping the revenue.
    """
    rows = timeline.get(student_id)
    if not rows:
        return None
    chosen = None
    for pay_date, rate in rows:
        if pay_date and pay_date <= on_date:
            chosen = rate
        else:
            break
    return chosen if chosen is not None else rows[0][1]


def school_average_hourly_rate(timeline: dict | None = None) -> Decimal:
    """Blended rate across every issued receipt -- the forecasting basis.

    Weighted by hours sold (total money / total hours), not a mean of rates,
    so big packages carry proportionate weight.
    """
    from .models import CoursePayment

    rows = (
        CoursePayment.objects
        .filter(status=CoursePayment.ReceiptStatus.ISSUED, sessions_granted__gt=0)
        .values_list("net_amount", "sessions_granted")
    )
    total_amount = ZERO
    total_hours = ZERO
    for net_amount, sessions in rows:
        amount = _d(net_amount)
        if amount <= 0 or not sessions:
            continue
        total_amount += amount
        total_hours += Decimal(sessions) * SESSION_HOURS
    if total_hours > 0:
        return _q(total_amount / total_hours)
    return ZERO


def suggest_revenue_per_student_hour(tutoring_class, timeline: dict | None = None) -> Decimal:
    """Average locked-in hourly rate of the students in this class.

    Each student contributes the rate from their own receipt; the class rate is
    the mean of those. Students with no receipt are skipped so they cannot drag
    the average down. Falls back to the school-wide blended rate, then to the
    class list price.
    """
    from .models import Enrollment

    if timeline is None:
        timeline = build_rate_timeline()

    student_ids = (
        Enrollment.objects
        .filter(tutoring_class=tutoring_class, is_active=True)
        .values_list("student_id", flat=True)
        .distinct()
    )
    today = date.today()
    rates = []
    for sid in student_ids:
        r = rate_on(timeline, sid, today)
        if r is not None and r > 0:
            rates.append(r)
    if rates:
        return _q(sum(rates) / Decimal(len(rates)))

    school = school_average_hourly_rate(timeline)
    if school > 0:
        return school

    price = _d(tutoring_class.course_price)
    if price > 0:
        return _q(price / (Decimal("10") * SESSION_HOURS))
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


# ============================================================ weekly series

def school_week_start(anchor: date) -> date:
    """School week runs Saturday -> Friday (classes are weekend-heavy)."""
    return anchor - timedelta(days=(anchor.weekday() - 5) % 7)


def recognized_revenue_rows(start: date, end: date, class_ids=None) -> list[dict]:
    """Revenue earned per attended session, valued at that student's own rate.

    Revenue is recognised when a session is consumed (`deducted=True`, i.e.
    present or no-show) -- not when the receipt is issued. That matches how the
    service is actually delivered, and is what makes weekly revenue meaningful.
    """
    from .models import Attendance

    qs = (
        Attendance.objects
        .filter(deducted=True, attendance_date__gte=start, attendance_date__lte=end)
    )
    if class_ids:
        qs = qs.filter(enrollment__tutoring_class_id__in=list(class_ids))

    rows = list(qs.values_list(
        "student_id", "attendance_date",
        "enrollment__tutoring_class_id", "enrollment__tutoring_class__name",
    ))
    timeline = build_rate_timeline({r[0] for r in rows if r[0]})
    fallback = school_average_hourly_rate(timeline)

    out = []
    for student_id, att_date, cls_id, cls_name in rows:
        rate = rate_on(timeline, student_id, att_date)
        estimated = rate is None
        if estimated:
            rate = fallback
        rate = rate or ZERO
        out.append({
            "student_id": student_id,
            "date": att_date,
            "class_id": cls_id,
            "class_name": cls_name or "-",
            "rate": rate,
            "hours": SESSION_HOURS,
            "revenue": rate * SESSION_HOURS,
            "estimated": estimated,
        })
    return out


def _weekly_costs(start: date, end: date, spread_fixed: bool) -> tuple[dict, dict]:
    """(teaching cost by week, other expense by week).

    Teaching cost comes from payroll entries; other expenses from SchoolExpense
    rows whose category is not flagged as payroll, so nothing is double counted.

    Rent-type costs land on a single day of the month, which makes raw weekly
    profit spike. `spread_fixed` averages each month's non-payroll expenses
    across that month's weeks instead -- usually the more readable view.
    """
    from .models import SchoolExpense, TutorPayrollEntry

    teaching: dict[date, Decimal] = {}
    for work_date, total in TutorPayrollEntry.objects.filter(
        work_date__gte=start, work_date__lte=end
    ).values_list("work_date", "total_amount"):
        wk = school_week_start(work_date)
        teaching[wk] = teaching.get(wk, ZERO) + _d(total)

    other: dict[date, Decimal] = {}
    expense_rows = (
        SchoolExpense.objects
        .select_related("category")
        .filter(expense_date__gte=start, expense_date__lte=end)
    )

    if not spread_fixed:
        for e in expense_rows:
            if e.category and e.category.is_tutor_payroll:
                continue
            wk = school_week_start(e.expense_date)
            other[wk] = other.get(wk, ZERO) + _d(e.amount)
        return teaching, other

    by_month: dict[tuple, Decimal] = {}
    for e in expense_rows:
        if e.category and e.category.is_tutor_payroll:
            continue
        key = (e.expense_date.year, e.expense_date.month)
        by_month[key] = by_month.get(key, ZERO) + _d(e.amount)

    weeks_in_month: dict[tuple, list] = {}
    cur = school_week_start(start)
    while cur <= end:
        weeks_in_month.setdefault((cur.year, cur.month), []).append(cur)
        cur += timedelta(days=7)

    for key, amount in by_month.items():
        weeks = weeks_in_month.get(key) or []
        if not weeks:
            continue
        share = amount / Decimal(len(weeks))
        for wk in weeks:
            other[wk] = other.get(wk, ZERO) + share

    return teaching, other


def weekly_breakdown(start: date, end: date, class_ids=None,
                     spread_fixed: bool = True) -> dict:
    """Week-by-week revenue / cost / profit / blended hourly rate."""
    revenue_rows = recognized_revenue_rows(start, end, class_ids)
    buckets: dict = {}

    def bucket(wk):
        return buckets.setdefault(wk, {
            "revenue": ZERO, "hours": ZERO, "sessions": 0,
            "students": set(), "classes": set(),
            "teaching_cost": ZERO, "other_cost": ZERO, "estimated_sessions": 0,
        })

    for r in revenue_rows:
        b = bucket(school_week_start(r["date"]))
        b["revenue"] += r["revenue"]
        b["hours"] += r["hours"]
        b["sessions"] += 1
        b["students"].add(r["student_id"])
        if r["class_id"]:
            b["classes"].add(r["class_id"])
        if r["estimated"]:
            b["estimated_sessions"] += 1

    # Costs are school-wide. Attributing them to a class-filtered view would be
    # misleading, so only fold them in when looking at the whole school.
    include_costs = not class_ids
    if include_costs:
        teaching, other = _weekly_costs(start, end, spread_fixed)
        for wk, amount in teaching.items():
            bucket(wk)["teaching_cost"] += amount
        for wk, amount in other.items():
            bucket(wk)["other_cost"] += amount

    empty = {
        "revenue": ZERO, "hours": ZERO, "sessions": 0, "students": set(),
        "classes": set(), "teaching_cost": ZERO, "other_cost": ZERO,
        "estimated_sessions": 0,
    }

    series = []
    cur = school_week_start(start)
    last = school_week_start(end)
    while cur <= last:
        b = buckets.get(cur, empty)
        total_cost = b["teaching_cost"] + b["other_cost"]
        profit = b["revenue"] - total_cost
        avg_rate = (b["revenue"] / b["hours"]) if b["hours"] > 0 else ZERO
        series.append({
            "week_start": cur.isoformat(),
            "label": cur.strftime("%d/%m"),
            "revenue": float(_q(b["revenue"])),
            "teaching_cost": float(_q(b["teaching_cost"])),
            "other_cost": float(_q(b["other_cost"])),
            "total_cost": float(_q(total_cost)),
            "profit": float(_q(profit)),
            "avg_rate": float(_q(avg_rate)),
            "hours": float(_q(b["hours"])),
            "sessions": b["sessions"],
            "students": len(b["students"]),
            "classes": len(b["classes"]),
            "margin": float(_q((profit / b["revenue"] * 100) if b["revenue"] > 0 else ZERO)),
            "estimated_sessions": b["estimated_sessions"],
        })
        cur += timedelta(days=7)

    total_rev = sum((_d(s["revenue"]) for s in series), ZERO)
    total_hours = sum((_d(s["hours"]) for s in series), ZERO)
    total_cost = sum((_d(s["total_cost"]) for s in series), ZERO)
    estimated = sum(s["estimated_sessions"] for s in series)
    total_sessions = sum(s["sessions"] for s in series)

    return {
        "series": series,
        "school_avg_rate": float(school_average_hourly_rate()),
        "costs_included": include_costs,
        "totals": {
            "revenue": float(_q(total_rev)),
            "cost": float(_q(total_cost)),
            "profit": float(_q(total_rev - total_cost)),
            "hours": float(_q(total_hours)),
            "sessions": total_sessions,
            "students": len({r["student_id"] for r in revenue_rows}),
            "avg_rate": float(_q((total_rev / total_hours) if total_hours > 0 else ZERO)),
            "margin": float(_q(((total_rev - total_cost) / total_rev * 100) if total_rev > 0 else ZERO)),
            "estimated_sessions": estimated,
            "estimated_pct": float(_q((Decimal(estimated) / Decimal(total_sessions) * 100)
                                      if total_sessions else ZERO, "0.1")),
        },
    }
