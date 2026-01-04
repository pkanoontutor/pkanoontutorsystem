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
