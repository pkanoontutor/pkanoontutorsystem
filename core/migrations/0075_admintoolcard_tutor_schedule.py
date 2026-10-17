from django.db import migrations

_URL = "/tutor-schedule/"


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if AdminToolCard.objects.filter(url=_URL).exists():
        return
    max_order = (
        AdminToolCard.objects.filter(section="operation")
        .order_by("-order").values_list("order", flat=True).first()
    ) or 0
    AdminToolCard.objects.create(
        section="operation",
        icon="🗓️",
        name="ตารางสอนติวเตอร์",
        desc="ตารางสอนสำหรับติวเตอร์เปิดดูเอง (ไม่ต้อง login) เลือกชื่อ/วิชาเพื่อไฮไลต์ และ Save / Share เป็นรูป",
        url=_URL,
        color="c-sky",
        order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    apps.get_model("core", "AdminToolCard").objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0074_renewal_installment_breakdown"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
