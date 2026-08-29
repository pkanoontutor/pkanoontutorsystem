# Generated manually for P'Kanoon Tutor
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0060_new_student_payment_notice_module"),
    ]

    operations = [
        migrations.CreateModel(
            name="TutorSheetMarkup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("page", models.PositiveIntegerField(verbose_name="หน้าที่")),
                ("strokes", models.JSONField(blank=True, default=list, verbose_name="ขีดเขียน")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tutor_markups", to="core.sheetdocument", verbose_name="เล่ม (ไฟล์ PDF)")),
                ("tutor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sheet_markups", to="core.teachingtutor", verbose_name="ติวเตอร์")),
            ],
            options={
                "verbose_name": "Tutor Sheet Markup",
                "verbose_name_plural": "Tutor Sheet Markups",
                "ordering": ("document", "page"),
            },
        ),
        migrations.AddConstraint(
            model_name="tutorsheetmarkup",
            constraint=models.UniqueConstraint(
                fields=("tutor", "document", "page"),
                name="uniq_tutor_sheet_markup_per_tutor_document_page",
            ),
        ),
    ]
