# Generated manually for P'Kanoon Tutor
from django.db import migrations

_URL = "/tutor-sheets/"


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
        icon="📖",
        name="ระบบชีทสำหรับติวเตอร์",
        desc="ติวเตอร์เข้าด้วย PIN เปิดชีท PDF ทีละหน้า สลับเนื้อหา/เฉลย และกดจบคาบเพื่อบันทึกหน้า/ข้อเข้าระบบอัปเดตชีท",
        url=_URL,
        color="c-teal",
        order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0058_tutor_sheet_reader"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
