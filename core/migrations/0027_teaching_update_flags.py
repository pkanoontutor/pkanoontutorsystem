# Generated for P'Kanoon Tutor teaching update improvements
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_fix_weekly_test_grade_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="teachingweeklyassignment",
            name="is_teaching",
            field=models.BooleanField(
                default=True,
                help_text="ใช้ปิดรายการที่สัปดาห์นี้ไม่มีสอน โดยยังเก็บ assignment ไว้ในระบบ",
                verbose_name="สัปดาห์นี้มีสอน",
            ),
        ),
        migrations.AddField(
            model_name="teachingprogressupdate",
            name="sheet_near_end",
            field=models.BooleanField(
                default=False,
                help_text="ติ๊กเมื่อชีทใกล้จบ เพื่อให้แสดงกรอบเตือนสีแดงในหน้าติวเตอร์",
                verbose_name="ใกล้จบชีท",
            ),
        ),
    ]
