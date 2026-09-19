from django import template

register = template.Library()


@register.filter
def get_item(obj, key):
    """
    ใช้กับ dict: mydict|get_item:somekey
    ใช้กับ object attribute: myobj|get_item:"field"
    ปลอดภัยกับ key ที่เป็น int
    """
    if obj is None:
        return None

    # dict access
    if isinstance(obj, dict):
        return obj.get(key)

    # attribute access (ต้องเป็น str เท่านั้น)
    if isinstance(key, str):
        return getattr(obj, key, None)

    return None


@register.filter
def index(seq, i):
    """
    ดึงสมาชิก list ตาม index: mylist|index:0
    ถ้าเกินขอบเขตให้คืน None
    """
    try:
        return seq[int(i)]
    except Exception:
        return None


@register.filter
def sessions(value):
    """Session counts read as "10" and "1.5", never "10.0" or "1.50".

    Half-day leave makes remaining_sessions a Decimal, and the bare Decimal
    renders with trailing zeros everywhere it is shown to parents and staff.
    """
    from decimal import Decimal, InvalidOperation
    if value in (None, ""):
        return "0"
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    d = d.normalize()
    if d == d.to_integral_value():
        return str(int(d))
    return f"{d:.1f}"
