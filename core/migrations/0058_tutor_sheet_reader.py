# Generated manually for P'Kanoon Tutor
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0057_admintoolcard_book_library"),
    ]

    operations = [
        migrations.AddField(
            model_name="teachingtutor",
            name="sheet_pin_hash",
            field=models.CharField(
                blank=True,
                help_text="ว่าง = ยังไม่เคยตั้ง PIN ระบบจะใช้ค่าเริ่มต้น 123456",
                max_length=255,
                verbose_name="รหัส PIN ระบบชีท (เข้ารหัส)",
            ),
        ),
        migrations.CreateModel(
            name="TutorSheetProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_page", models.PositiveIntegerField(default=1, verbose_name="หน้าล่าสุด")),
                ("last_question", models.CharField(blank=True, max_length=50, verbose_name="ข้อล่าสุด")),
                ("updated_by_name", models.CharField(blank=True, max_length=120, verbose_name="ผู้บันทึกล่าสุด")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tutor_progress", to="core.sheetdocument", verbose_name="ไฟล์ที่เปิดค้างไว้")),
                ("sheet", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tutor_progress", to="core.sheet", verbose_name="ชีท")),
                ("tutoring_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tutor_sheet_progress", to="core.tutoringclass", verbose_name="คลาส")),
            ],
            options={
                "verbose_name": "Tutor Sheet Progress",
                "verbose_name_plural": "Tutor Sheet Progress",
                "ordering": ("-updated_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="tutorsheetprogress",
            constraint=models.UniqueConstraint(
                fields=("tutoring_class", "sheet"),
                name="uniq_tutor_sheet_progress_per_class_sheet",
            ),
        ),
    ]
