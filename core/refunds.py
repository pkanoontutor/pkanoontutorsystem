"""ใบคืนเงิน (refund receipts). Each refund books a SchoolExpense in the
"คืนเงิน" category, so it is deducted in every income/expense summary."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AdmissionInquiry, ExpenseCategory, RefundReceipt, SchoolExpense, Student

REFUND_CATEGORY = "คืนเงิน"
T = RefundReceipt.RecipientType


def _staff(user) -> bool:
    return user.is_authenticated and user.is_staff


def _money(raw) -> Decimal | None:
    try:
        v = Decimal(str(raw).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return v.quantize(Decimal("0.01")) if v.is_finite() and v > 0 else None


def next_refund_no(on) -> str:
    prefix = f"RF{(on.year + 543) % 100:02d}-"
    last = (RefundReceipt.objects.filter(refund_no__startswith=prefix)
            .order_by("-refund_no").values_list("refund_no", flat=True).first())
    n = int(last.split("-")[1]) + 1 if last else 1
    return f"{prefix}{n:04d}"


def _people():
    students = [
        {"id": s.id, "label": f"{s.nickname or '-'} | {s.full_name} | {s.student_code or '-'}{'' if s.is_active else ' (inactive)'}",
         "name": s.full_name, "phone": s.parent_phone or ""}
        for s in Student.objects.order_by("-is_active", "nickname")
    ]
    admissions = [
        {"id": a.id, "label": f"{a.nickname} | {a.first_name} {a.last_name} | {a.contact_phone}",
         "name": f"{a.first_name} {a.last_name}".strip(), "phone": a.contact_phone or ""}
        for a in AdmissionInquiry.objects.order_by("-id")
    ]
    return students, admissions


@login_required
def refund_list(request: HttpRequest) -> HttpResponse:
    if not _staff(request.user):
        return HttpResponse(status=403)
    form, errors = {}, []
    if request.method == "POST":
        form = request.POST
        kind = form.get("recipient_type")
        student = admission = None
        name = " ".join((form.get("recipient_name") or "").split())
        phone = (form.get("recipient_phone") or "").strip()[:50]
        if kind == T.STUDENT:
            student = Student.objects.filter(id=form.get("student_id") or 0).first()
            if not student:
                errors.append("กรุณาเลือกนักเรียนจากรายการค้นหา")
        elif kind == T.ADMISSION:
            admission = AdmissionInquiry.objects.filter(id=form.get("admission_id") or 0).first()
            if not admission:
                errors.append("กรุณาเลือกผู้สมัครจากรายการค้นหา")
        elif kind != T.EXTERNAL:
            errors.append("กรุณาเลือกประเภทผู้รับเงินคืน")
        if student and not name:
            name = student.full_name
        if admission and not name:
            name = f"{admission.first_name} {admission.last_name}".strip()
        if not name:
            errors.append("กรุณากรอกชื่อผู้รับเงินคืน")
        items = []
        for desc, amt in zip(form.getlist("item_desc"), form.getlist("item_amount")):
            desc = " ".join(desc.split())[:200]
            if not desc and not amt.strip():
                continue
            value = _money(amt)
            if not desc or value is None:
                errors.append("แต่ละรายการต้องมีทั้งรายละเอียดและยอดเงินมากกว่า 0")
                break
            items.append({"desc": desc, "amount": str(value)})
        if not items and not errors:
            errors.append("กรุณาระบุรายการคืนเงินอย่างน้อย 1 รายการ")
        try:
            refund_date = date.fromisoformat(form.get("refund_date") or "")
        except ValueError:
            refund_date = timezone.localdate()
        method = form.get("payment_method")
        if method not in dict(SchoolExpense.PaymentMethod.choices):
            method = SchoolExpense.PaymentMethod.TRANSFER
        if not errors:
            total = sum((Decimal(i["amount"]) for i in items), Decimal("0"))
            reason = (form.get("reason") or "").strip()
            with transaction.atomic():
                cat, _ = ExpenseCategory.objects.get_or_create(name=REFUND_CATEGORY, defaults={"sort_order": 99})
                r = RefundReceipt.objects.create(
                    refund_no=next_refund_no(refund_date), refund_date=refund_date, recipient_type=kind,
                    student=student, admission=admission, recipient_name=name[:255], recipient_phone=phone,
                    items=items, amount=total, payment_method=method, reason=reason,
                    created_by=request.user.get_username(),
                )
                r.expense = SchoolExpense.objects.create(
                    expense_date=refund_date, category=cat, vendor=name[:255], amount=total, payment_method=method,
                    description=f"ใบคืนเงิน {r.refund_no}: " + ", ".join(i["desc"] for i in items)[:200],
                    note=reason,
                )
                r.save(update_fields=["expense"])
            messages.success(request, f"ออกใบคืนเงิน {r.refund_no} แล้ว · บันทึกเป็นรายจ่าย {total:,.2f} บาท")
            return redirect("core:refund_detail", pk=r.pk)
    students, admissions = _people()
    refunds = list(RefundReceipt.objects.select_related("student", "admission")[:200])
    month_start = timezone.localdate().replace(day=1)
    return render(request, "core/refund_list.html", {
        "refunds": refunds, "errors": errors, "form": form,
        "form_items": [[d, a] for d, a in zip(form.getlist("item_desc"), form.getlist("item_amount")) if d or a] if form else [],
        "students": students, "admissions": admissions,
        "methods": SchoolExpense.PaymentMethod.choices, "types": T.choices,
        "today": timezone.localdate(),
        "month_total": sum((r.amount for r in refunds if not r.is_void and r.refund_date >= month_start), Decimal("0")),
    })


@login_required
def refund_detail(request: HttpRequest, pk: int) -> HttpResponse:
    if not _staff(request.user):
        return HttpResponse(status=403)
    r = get_object_or_404(RefundReceipt, pk=pk)
    items = [{"desc": i.get("desc", ""), "amount": Decimal(str(i.get("amount", "0")))} for i in r.items]
    return render(request, "core/refund_detail.html", {"r": r, "items": items})


@login_required
@require_POST
def refund_void(request: HttpRequest, pk: int) -> HttpResponse:
    if not _staff(request.user):
        return HttpResponse(status=403)
    r = get_object_or_404(RefundReceipt, pk=pk)
    if not r.is_void:
        with transaction.atomic():
            if r.expense_id:
                SchoolExpense.objects.filter(pk=r.expense_id).delete()
            r.is_void = True
            r.expense = None
            r.save(update_fields=["is_void", "expense"])
        messages.success(request, f"ยกเลิกใบคืนเงิน {r.refund_no} แล้ว · ลบรายจ่ายที่ผูกไว้ออก")
    return redirect("core:refund_detail", pk=r.pk)
