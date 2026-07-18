# Generated manually for P'Kanoon Tutor
from django.db import migrations

_URL = "/online-course-p6/videos/"


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
        icon="🎬",
        name="จัดการคลิปติวออนไลน์ ป.6",
        desc="วางลิงก์คลิป Google Drive แล้วฝังเล่นวิดีโอในหน้าคอร์สออนไลน์ให้ผู้ปกครอง/นักเรียนดูได้เลย ไม่ต้องเปิดโฟลเดอร์ Drive เอง",
        url=_URL,
        color="c-rose",
        order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0036_onlinecoursevideo"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
