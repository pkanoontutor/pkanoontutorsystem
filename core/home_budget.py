"""🏠 Home decoration budget -- a personal module, unrelated to tutoring.

One page (/home-budget/) driven by a small JSON API: every action returns
the whole state, so totals and "what's left" update instantly.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import HomeBudgetExpense, HomeBudgetItem, HomeBudgetProject, HomeBudgetZone

ZERO = Decimal("0")
# The supplied plans (cropped + mirrored to match the house's orientation);
# an uploaded image for a floor replaces its default.
DEFAULT_PLANS = {1: "core/home_plans/floor1.jpg", 2: "core/home_plans/floor2.jpg"}
ZONE_COLORS = ["#6366f1", "#f97316", "#10b981", "#ec4899", "#0ea5e9", "#eab308", "#8b5cf6", "#ef4444", "#14b8a6", "#64748b"]


def _project() -> HomeBudgetProject:
    p = HomeBudgetProject.objects.order_by("id").first()
    return p or HomeBudgetProject.objects.create()


def _money(raw, default=ZERO) -> Decimal:
    try:
        v = Decimal(str(raw).replace(",", "").strip())
        return v if v >= 0 else default
    except (InvalidOperation, ValueError, TypeError):
        return default


def _float_or_none(raw):
    try:
        return max(0.0, min(100.0, float(raw)))
    except (TypeError, ValueError):
        return None


def _num(d: Decimal) -> float:
    return float(d or 0)


def _state(p: HomeBudgetProject) -> dict:
    zones = list(p.zones.all())
    items = list(p.items.select_related("zone").prefetch_related("expenses"))
    zone_rows = {z.id: {"id": z.id, "name": z.name, "color": z.color,
                        "budget": _num(z.budget) if z.budget is not None else None,
                        "rect": ([z.plan_x, z.plan_y, z.plan_w, z.plan_h] if z.plan_w else None),
                        "floor": z.floor or 1,
                        "planned": 0.0, "spent": 0.0, "count": 0} for z in zones}
    item_rows = []
    totals = {"planned": ZERO, "spent": ZERO, "committed": ZERO, "items_spent": ZERO, "labor_spent": ZERO}
    unzoned = {"planned": 0.0, "spent": 0.0, "count": 0}
    for it in items:
        spent = sum((e.amount for e in it.expenses.all()), ZERO)
        planned = it.planned_amount or ZERO
        totals["planned"] += planned
        totals["spent"] += spent
        # what this line will cost: the plan until money is spent, then whichever is higher
        totals["committed"] += max(planned, spent) if not it.is_done else spent
        totals["labor_spent" if it.kind == "labor" else "items_spent"] += spent
        bucket = zone_rows.get(it.zone_id) or unzoned
        bucket["planned"] += _num(planned)
        bucket["spent"] += _num(spent)
        bucket["count"] += 1
        item_rows.append({
            "id": it.id, "name": it.name, "kind": it.kind, "zone_id": it.zone_id,
            "planned": _num(planned), "spent": _num(spent), "vendor": it.vendor, "note": it.note,
            "is_done": it.is_done,
            "expenses": [{"id": e.id, "date": e.spent_on.isoformat(), "amount": _num(e.amount), "note": e.note,
                          "receipt_url": e.receipt.url if e.receipt else "",
                          "receipt_name": (e.receipt.name.rsplit("/", 1)[-1] if e.receipt else "")}
                         for e in it.expenses.all()],
        })
    budget = p.total_budget or ZERO
    return {
        "project": {"name": p.name, "budget": _num(budget),
                    "floor_plans": {
                        "1": p.floor_plan.url if p.floor_plan else static(DEFAULT_PLANS[1]),
                        "2": p.floor_plan_2.url if p.floor_plan_2 else static(DEFAULT_PLANS[2]),
                    },
                    "custom_plans": {"1": bool(p.floor_plan), "2": bool(p.floor_plan_2)}},
        "zones": list(zone_rows.values()),
        "unzoned": unzoned,
        "items": item_rows,
        "totals": {
            "budget": _num(budget),
            "planned": _num(totals["planned"]),
            "spent": _num(totals["spent"]),
            "committed": _num(totals["committed"]),
            "remaining": _num(budget - totals["spent"]),
            "remaining_after_plan": _num(budget - totals["committed"]),
            "items_spent": _num(totals["items_spent"]),
            "labor_spent": _num(totals["labor_spent"]),
        },
    }


@login_required
def home_budget_page(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        return HttpResponse(status=403)
    p = _project()
    return render(request, "core/home_budget.html", {
        "state": _state(p),
        "today": timezone.localdate(),
    })


@require_POST
@login_required
def home_budget_api(request: HttpRequest) -> JsonResponse:
    """All edits (multipart, so receipts and the floor plan can ride along)."""
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    p = _project()
    P = request.POST
    act = (P.get("do") or "").strip()
    zone = HomeBudgetZone.objects.filter(project=p, id=P.get("zone_id") or 0).first() if P.get("zone_id") else None
    item = HomeBudgetItem.objects.filter(project=p, id=P.get("item_id") or 0).first() if P.get("item_id") else None

    def err(msg):
        return JsonResponse({"ok": False, "error": msg}, status=400)

    if act == "set_project":
        p.total_budget = _money(P.get("budget"), p.total_budget)
        p.name = (P.get("name") or p.name).strip()[:120]
        p.save()
    elif act == "add_zone":
        name = (P.get("name") or "").strip()[:80]
        if not name:
            return err("กรุณาตั้งชื่อโซน")
        HomeBudgetZone.objects.create(project=p, name=name,
                                      color=(P.get("color") or ZONE_COLORS[p.zones.count() % len(ZONE_COLORS)])[:20],
                                      floor=2 if P.get("floor") == "2" else 1,
                                      order=p.zones.count())
    elif act == "update_zone" and zone:
        zone.name = (P.get("name") or zone.name).strip()[:80]
        zone.color = (P.get("color") or zone.color)[:20]
        zone.budget = _money(P.get("budget")) if (P.get("budget") or "").strip() else None
        if P.get("floor") in ("1", "2"):
            zone.floor = int(P.get("floor"))
        zone.save()
    elif act == "delete_zone" and zone:
        zone.delete()  # items keep existing, just become "ไม่ระบุโซน"
    elif act == "set_zone_rect" and zone:
        if P.get("clear"):
            zone.plan_x = zone.plan_y = zone.plan_w = zone.plan_h = None
        else:
            zone.plan_x, zone.plan_y = _float_or_none(P.get("x")), _float_or_none(P.get("y"))
            zone.plan_w, zone.plan_h = _float_or_none(P.get("w")), _float_or_none(P.get("h"))
        zone.save()
    elif act in ("add_item", "update_item"):
        name = (P.get("name") or "").strip()[:200]
        if not name:
            return err("กรุณาใส่ชื่อรายการ")
        target = item if act == "update_item" else HomeBudgetItem(project=p)
        if act == "update_item" and not item:
            return err("ไม่พบรายการ")
        target.name = name
        target.kind = P.get("kind") if P.get("kind") in ("item", "labor") else "item"
        target.zone = HomeBudgetZone.objects.filter(project=p, id=P.get("item_zone") or 0).first() if P.get("item_zone") else None
        target.planned_amount = _money(P.get("planned"))
        target.vendor = (P.get("vendor") or "").strip()[:150]
        target.note = (P.get("note") or "").strip()[:300]
        target.save()
    elif act == "toggle_done" and item:
        item.is_done = not item.is_done
        item.save(update_fields=["is_done"])
    elif act == "delete_item" and item:
        for e in item.expenses.all():
            if e.receipt:
                e.receipt.delete(save=False)
        item.delete()
    elif act == "add_expense" and item:
        amount = _money(P.get("amount"), None)
        if not amount:
            return err("กรุณาใส่จำนวนเงินที่จ่ายจริง")
        from django.utils.dateparse import parse_date
        e = HomeBudgetExpense(item=item, amount=amount, note=(P.get("note") or "").strip()[:300],
                              spent_on=parse_date(P.get("date") or "") or timezone.localdate())
        if request.FILES.get("receipt"):
            e.receipt = request.FILES["receipt"]
        e.save()
    elif act == "delete_expense":
        e = HomeBudgetExpense.objects.filter(item__project=p, id=P.get("expense_id") or 0).first()
        if e:
            if e.receipt:
                e.receipt.delete(save=False)
            e.delete()
    elif act == "upload_plan":
        f = request.FILES.get("plan")
        if not f or not (f.content_type or "").startswith("image/"):
            return err("แปลนต้องเป็นไฟล์รูปภาพ")
        field = "floor_plan_2" if P.get("floor") == "2" else "floor_plan"
        if getattr(p, field):
            getattr(p, field).delete(save=False)
        setattr(p, field, f)
        p.save()
    elif act == "remove_plan":   # back to the default plan for that floor
        field = "floor_plan_2" if P.get("floor") == "2" else "floor_plan"
        if getattr(p, field):
            getattr(p, field).delete(save=False)
        setattr(p, field, None)
        p.save()
    else:
        return err("ไม่รู้จักคำสั่งนี้")
    return JsonResponse({"ok": True, "state": _state(p)})


EXTRA_SYSTEMS = [
    {"icon": "🏠", "name": "งบตกแต่งบ้าน", "desc": "วางแผนงบซื้อของและค่าแรง แยกตามโซนในบ้าน บันทึกค่าใช้จ่ายจริงพร้อมใบเสร็จ และดูบนแปลนบ้าน", "url": "/home-budget/"},
]


@login_required
def extras_hub(request: HttpRequest) -> HttpResponse:
    """ระบบส่วนเสริม -- personal tools that aren't part of the tutoring school."""
    if not request.user.is_staff:
        return HttpResponse(status=403)
    return render(request, "core/extras_hub.html", {"systems": EXTRA_SYSTEMS})
