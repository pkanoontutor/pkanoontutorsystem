# Generated manually for P'Kanoon Tutor
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0035_schedule_tutor_integration"),
    ]

    operations = [
        migrations.CreateModel(
            name="OnlineCourseVideo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("course_key", models.CharField(default="p6", help_text="ใช้แยกชุดคลิปตามคอร์ส เช่น p6", max_length=50, verbose_name="รหัสคอร์ส")),
                ("title", models.CharField(max_length=255, verbose_name="ชื่อคลิป")),
                ("drive_url", models.URLField(help_text="วางลิงก์แชร์ไฟล์วิดีโอจาก Google Drive (ต้องแชร์แบบ 'ทุกคนที่มีลิงก์ดูได้')", max_length=1000, verbose_name="ลิงก์ Google Drive")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ (เช่น สัปดาห์ที่สอน)")),
                ("display_order", models.PositiveIntegerField(default=1, verbose_name="ลำดับแสดงผล")),
                ("is_active", models.BooleanField(default=True, verbose_name="แสดงให้ดู")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Online Course Video",
                "verbose_name_plural": "Online Course Videos",
                "ordering": ("course_key", "display_order", "-created_at"),
            },
        ),
    ]
