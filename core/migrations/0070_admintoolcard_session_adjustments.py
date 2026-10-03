# Generated manually for P'Kanoon Tutor
from django.db import migrations

_URL = "/session-adjustments/"


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if AdminToolCard.objects.filter(url=_URL).exists():
        return
    max_order = (
        AdminToolCard.objects.filter(section="private")
        .order_by("-order").values_list("order", flat=True).first()
    ) or 0
    AdminToolCard.objects.create(
        section="private",
        icon="✏️",
        name="ปรับจำนวนครั้งเรียน",
        desc="เพิ่ม / ลดจำนวนครั้งเรียนพร้อมเหตุผล แล้วได้ใบแจ้งให้ Copy / Save ส่งผู้ปกครอง พร้อมวันที่คาดว่าจะครบคอร์สใหม่",
        url=_URL,
        color="c-sand",
        order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0069_packages_adjustments_signup_paid"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
