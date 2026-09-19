from decimal import Decimal

from django.db import migrations, models


def backfill_units(apps, schema_editor):
    """Existing rows: 1 unit if they consumed a session, else 0.

    Done as two bulk UPDATEs rather than row-by-row -- the attendance table
    is the largest in the system and this runs inside the deploy.
    """
    Attendance = apps.get_model("core", "Attendance")
    Attendance.objects.filter(deducted=True).update(deducted_units=Decimal("1"))
    Attendance.objects.filter(deducted=False).update(deducted_units=Decimal("0"))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    """Half-session deduction for leave ("ลาแบบหัก 0.5 ครั้ง").

    Hand-written: the local venv runs Django 6.0 against a 4.2.16 pin, so
    autodetect output would carry unrelated pre-existing drift.
    """

    dependencies = [
        ("core", "0066_admintoolcard_class_videos"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendance",
            name="deducted_units",
            field=models.DecimalField(
                decimal_places=1,
                default=Decimal("1"),
                help_text="1 = หักเต็มครั้ง, 0.5 = ลาแบบหักครึ่ง, 0 = ลาแบบไม่หัก",
                max_digits=4,
                verbose_name="จำนวนครั้งที่หัก",
            ),
        ),
        migrations.AlterField(
            model_name="attendance",
            name="status",
            field=models.CharField(
                choices=[
                    ("present", "มาเรียน (หัก 1 ครั้ง)"),
                    ("excused", "ลาเรียน (ไม่หักครั้ง)"),
                    ("excused_half", "ลาเรียน (หัก 0.5 ครั้ง)"),
                    ("no_show", "ขาดเรียนโดยไม่แจ้ง (หัก 1 ครั้ง)"),
                ],
                default="present",
                max_length=20,
                verbose_name="สถานะ",
            ),
        ),
        migrations.RunPython(backfill_units, noop),
    ]
