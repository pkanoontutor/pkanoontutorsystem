# Generated manually for P'Kanoon Tutor
from django.db import migrations

_URL = "/class-videos/"


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
        name="คลิปเรียนย้อนหลัง",
        desc="ใส่ลิงก์ YouTube 4 คาบต่อวันต่อคลาส ดึงวิชา/ติวเตอร์จากตารางสอนอัตโนมัติ แล้วเผยแพร่ให้ผู้ปกครองดูที่ /video-replay/",
        url=_URL,
        color="c-rose",
        order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0065_class_video_replay"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
