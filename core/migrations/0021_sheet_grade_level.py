# Generated for adding grade level to Sheet.
from django.db import migrations, models
import re


def infer_grade_from_text(*texts):
    combined = " ".join((t or "") for t in texts).lower()
    for grade in ["p4", "p5", "p6", "m1", "m2", "m3", "m4"]:
        if re.search(rf"(^|[^a-z0-9]){grade}([^a-z0-9]|$)", combined, re.I):
            return grade
    compact = combined.replace(".", "").replace(" ", "")
    mapping = {
        "ป4": "p4", "ป5": "p5", "ป6": "p6",
        "ม1": "m1", "ม2": "m2", "ม3": "m3", "ม4": "m4",
    }
    for key, value in mapping.items():
        if key in compact:
            return value
    return ""


def populate_sheet_grade_level(apps, schema_editor):
    Sheet = apps.get_model("core", "Sheet")
    for sheet in Sheet.objects.all():
        grade = infer_grade_from_text(sheet.code, sheet.title)
        if grade:
            sheet.grade_level = grade
            sheet.save(update_fields=["grade_level"])


def reverse_populate_sheet_grade_level(apps, schema_editor):
    # Keep existing data on rollback safety; field removal will be handled by Django if migration is reversed.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_sheet_print_order_module"),
    ]

    operations = [
        migrations.AddField(
            model_name="sheet",
            name="grade_level",
            field=models.CharField(
                "ระดับชั้น",
                blank=True,
                choices=[
                    ("p4", "ป.4"),
                    ("p5", "ป.5"),
                    ("p6", "ป.6"),
                    ("m1", "ม.1"),
                    ("m2", "ม.2"),
                    ("m3", "ม.3"),
                    ("m4", "ม.4"),
                ],
                default="",
                help_text="ใช้จัดกลุ่มชีทใน Sheet Inventory และช่วย filter ชีทให้ตรงกับ class",
                max_length=20,
            ),
        ),
        migrations.RunPython(populate_sheet_grade_level, reverse_populate_sheet_grade_level),
    ]
