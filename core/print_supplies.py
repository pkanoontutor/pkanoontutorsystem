"""📦 Print-shop consumables: paper, spines, ink, drums.

Sending an order to print takes its paper out of stock straight away. The spine
comes out when the print shop picks a size for the order (colour is set by the
order, size by the shop); changing the size puts the old ones back. Ink and
drums have no per-order usage, so they only change by hand. Every change writes
a PrintSupplyLog row. A4 is entered in reams but stored and deducted in
sheets (cover paper is entered in sheets). Like /print-shop/ itself these pages need no login.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import PrintSupply, PrintSupplyLog, SheetDocument, SheetPrintOrder

C = PrintSupply.Category


def _actor(request: HttpRequest) -> str:
    if request.user.is_authenticated:
        return request.user.get_username()
    return (request.POST.get("actor") or "").strip()[:100] or "ร้านปรินท์"


def _change(supply_id: int, delta: int, reason: str, actor: str, note: str = "", order=None) -> None:
    with transaction.atomic():
        PrintSupply.objects.filter(id=supply_id).update(quantity=F("quantity") + delta)
        supply = PrintSupply.objects.select_for_update().get(id=supply_id)
        PrintSupplyLog.objects.create(supply=supply, delta=delta, balance_after=supply.quantity,
                                      reason=reason, actor=actor, note=note[:255], order=order)


def sheets_for_pages(pages: int, sides: str) -> int:
    if sides == SheetPrintOrder.PrintSides.DOUBLE:
        return (pages + 1) // 2
    return pages


def clean_sides(raw) -> str:
    return raw if raw in dict(SheetPrintOrder.PrintSides.choices) else SheetPrintOrder.PrintSides.SINGLE


def clean_pages(raw) -> int:
    try:
        return max(int(raw or 0), 0)
    except (TypeError, ValueError):
        return 0


def deduct_paper_for_order(order: SheetPrintOrder, actor: str) -> None:
    """Pages per book come from the sheet's uploaded PDFs (its recorded page
    count if none); a custom document's come from the order form. A sheet
    book takes 1 cover sheet."""
    content_pages = 0
    if order.sheet_id:
        pages = SheetDocument.objects.filter(sheet_id=order.sheet_id, kind=SheetDocument.Kind.CONTENT).values_list("page_count", flat=True)
        content_pages = sum(int(p or 0) for p in pages) or int(order.sheet.total_pages or 0)
    else:
        content_pages = int(order.content_pages or 0)
    covers = order.quantity if order.sheet_id else 0
    a4 = order.quantity * sheets_for_pages(content_pages, order.print_sides)
    order.content_pages = content_pages
    order.covers_used = covers
    order.a4_used = a4
    order.save(update_fields=["content_pages", "covers_used", "a4_used", "updated_at"])
    note = f"{order.display_code} {order.quantity} เล่ม · {content_pages} หน้า · {order.get_print_sides_display()}"
    for category, used in ((C.COVER_PAPER, covers), (C.A4_PAPER, a4)):
        supply = PrintSupply.objects.filter(category=category).first()
        if supply and used:
            _change(supply.id, -used, PrintSupplyLog.Reason.ORDER, actor, note, order)


def spine_options(order: SheetPrintOrder, spines: list) -> list:
    if order.binding_type != SheetPrintOrder.BindingType.SIDE:
        return []
    return [s for s in spines if s.is_active and (not order.spine_color or s.spine_color == order.spine_color)]


def active_spines() -> list:
    return list(PrintSupply.objects.filter(category=C.SPINE, is_active=True))


def stock_rows() -> list:
    return list(PrintSupply.objects.filter(is_active=True))


def low_stock_alerts(rows=None) -> list:
    """What's running out, including a spine colour with no stock row at all."""
    rows = stock_rows() if rows is None else rows
    alerts = [{"name": s.name, "left": s.quantity_label + (f" ({s.reams_label})" if s.reams_label else "")} for s in rows if s.is_low]
    have = {s.spine_color for s in rows if s.category == C.SPINE}
    for value, label in SheetPrintOrder.SpineColor.choices:
        if value not in have:
            alerts.append({"name": f"สัน{label}", "left": "ยังไม่มีในสต๊อก"})
    return alerts


def editor_context(rows=None, next_page: str = "") -> dict:
    rows = stock_rows() if rows is None else rows
    return {
        "supply_rows": rows,
        "supply_groups": [(label, [s for s in rows if s.category == value]) for value, label in C.choices],
        "supply_colors": SheetPrintOrder.SpineColor.choices,
        "supply_next": next_page,
        "supply_alerts": low_stock_alerts(rows),
    }


def _back(request: HttpRequest) -> HttpResponse:
    if request.POST.get("next") == "shop":
        return redirect(reverse("core:print_shop_order_list") + "?supplies=1#supplies")
    return redirect("core:print_supplies")


def _amount(supply: PrintSupply, raw) -> int | None:
    """The typed amount in stock units: A4 is typed in reams."""
    try:
        value = Decimal(str(raw).strip())
        if not value.is_finite():
            return None
        if supply.in_reams:
            value *= PrintSupply.SHEETS_PER_REAM
        return int(value)
    except (InvalidOperation, ValueError, OverflowError):
        return None


@require_POST
def print_shop_pick_spine(request: HttpRequest, pk: int) -> HttpResponse:
    actor = _actor(request)
    with transaction.atomic():
        order = get_object_or_404(SheetPrintOrder.objects.select_for_update(of=("self",)).select_related("sheet"), pk=pk)
        new = PrintSupply.objects.filter(id=clean_pages(request.POST.get("spine_supply")), category=C.SPINE).first()
        if order.status != SheetPrintOrder.Status.PENDING or order.binding_type != SheetPrintOrder.BindingType.SIDE:
            return redirect("core:print_shop_order_list")
        if (new.id if new else None) != order.spine_supply_id:
            label = f"{order.display_code} {order.quantity} เล่ม"
            if order.spine_supply_id:
                _change(order.spine_supply_id, order.spine_used, PrintSupplyLog.Reason.SPINE_RETURN, actor, label, order)
            if new:
                _change(new.id, -order.quantity, PrintSupplyLog.Reason.SPINE, actor, label, order)
            order.spine_supply = new
            order.spine_used = order.quantity if new else 0
            order.save(update_fields=["spine_supply", "spine_used", "updated_at"])
    return redirect("core:print_shop_order_list")


def print_supplies_page(request: HttpRequest) -> HttpResponse:
    logs = PrintSupplyLog.objects.select_related("supply", "order")
    picked = clean_pages(request.GET.get("supply"))
    if picked:
        logs = logs.filter(supply_id=picked)
    rows = stock_rows()
    return render(request, "core/print_supplies.html", {
        **editor_context(rows),
        "logs": logs[:200],
        "picked": picked,
    })


@require_POST
def print_supply_update(request: HttpRequest) -> HttpResponse:
    actor = _actor(request)
    action = request.POST.get("action")
    note = (request.POST.get("note") or "").strip()
    if action == "add_spine":
        color = request.POST.get("spine_color")
        size = (request.POST.get("spine_size") or "").strip()[:30]
        if color in dict(SheetPrintOrder.SpineColor.choices) and size:
            spine, created = PrintSupply.objects.get_or_create(
                category=C.SPINE, spine_color=color, spine_size=size,
                defaults={"name": f"สัน{dict(SheetPrintOrder.SpineColor.choices)[color]} {size}", "unit": "อัน"},
            )
            if not spine.is_active:
                spine.is_active = True
                spine.save(update_fields=["is_active"])
            qty = clean_pages(request.POST.get("quantity"))
            if qty:
                _change(spine.id, qty, PrintSupplyLog.Reason.ADJUST, actor, note or "ตั้งต้นขนาดสันใหม่")
        return _back(request)
    supply = get_object_or_404(PrintSupply, id=clean_pages(request.POST.get("supply")))
    if action == "hide" and supply.category == C.SPINE:
        supply.is_active = False
        supply.save(update_fields=["is_active"])
    elif action in ("add", "remove", "set"):
        amount = _amount(supply, request.POST.get("amount"))
        if amount is None:
            return _back(request)
        if action == "set":
            delta = amount - supply.quantity
        else:
            delta = abs(amount) if action == "add" else -abs(amount)
        if delta:
            _change(supply.id, delta, PrintSupplyLog.Reason.ADJUST, actor, note)
    return _back(request)
