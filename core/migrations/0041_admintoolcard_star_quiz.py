# Generated manually for P'Kanoon Tutor
from django.db import migrations

_URL = "/star-quiz/manage/"


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
        icon="⭐",
        name="ระบบเทสเก็บดาว",
        desc="สร้างเทสรายสัปดาห์ (ข้อกา/ข้อเขียน) ตามระดับชั้น ให้นักเรียนทำสะสมดาว และดูคะแนนสะสมของแต่ละคนได้",
        url=_URL,
        color="c-sand",
        order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0040_star_quiz_system"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
