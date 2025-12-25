from django import template

register = template.Library()


@register.filter
def get_item(obj, key):
    """
    ใช้กับ dict: mydict|get_item:somekey
    และใช้กับ object ที่มี attribute: myobj|get_item:"field"
    """
    if obj is None:
        return None
    # dict
    if isinstance(obj, dict):
        return obj.get(key)
    # object attribute
    return getattr(obj, key, None)


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
