
# Generated manually for Pkanoon Tutor: staging area for sheet PDF uploads.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0062_new_student_payment_notice_pricing_option"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StagedSheetDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="sheet_staging/", verbose_name="ไฟล์ PDF")),
                ("original_filename", models.CharField(max_length=255, verbose_name="ชื่อไฟล์เดิม")),
                ("file_size", models.PositiveBigIntegerField(default=0, verbose_name="ขนาดไฟล์ (bytes)")),
                ("uploaded_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่อัปโหลด")),
                ("linked_at", models.DateTimeField(blank=True, null=True, verbose_name="วันที่เชื่อมกับชีท")),
                ("linked_document", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="staged_source", to="core.sheetdocument", verbose_name="ไฟล์ที่เชื่อมแล้ว")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="staged_sheet_documents", to=settings.AUTH_USER_MODEL, verbose_name="ผู้อัปโหลด")),
            ],
            options={
                "verbose_name": "Staged Sheet Document",
                "verbose_name_plural": "Staged Sheet Documents",
                "ordering": ("-uploaded_at",),
            },
        ),
    ]
