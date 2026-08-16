# Generated manually for P'Kanoon Tutor
from django.db import migrations

_URL = "/remaining-attendance/"


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
        icon="🔎",
        name="Remaining Attendance",
        desc="เสิร์ชชื่อเด็ก ดูครั้งเรียนคงเหลือ คาดว่าจะครบคอร์สวันไหน ประวัติมา/ลา/ขาดล่าสุด และประวัติการชำระเงินต่อคอร์ส",
        url=_URL,
        color="c-stone",
        order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0054_admissioninquiry_attended_first_lesson"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
