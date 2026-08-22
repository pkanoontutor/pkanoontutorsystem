# Generated manually for P'Kanoon Tutor
from django.db import migrations

_URL = "/books/"


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
        icon="📚",
        name="คลังหนังสือ",
        desc="บันทึกโปรไฟล์หนังสือต้นทางที่ใช้ทำชีท ชื่อ/รหัส/วิชา/ระดับชั้น ลิงก์ไฟล์ และรูปปก",
        url=_URL,
        color="c-lilac",
        order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0056_book_library_and_sheet_documents"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
