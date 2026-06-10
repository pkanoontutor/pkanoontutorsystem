# Generated manually for Pkanoon weekly small test module.
# Put this file after 0024_super_dashboard_ops_fields.py in core/migrations/.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0024_super_dashboard_ops_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeeklyTest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "week_start",
                    models.DateField(
                        help_text="ระบบใช้สัปดาห์เดียวกับ Dashboard: เสาร์-อาทิตย์",
                        verbose_name="สัปดาห์ที่เริ่มวันเสาร์",
                    ),
                ),
                ("test_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="วันที่แสดงบนใบประกาศ")),
                (
                    "subject_name",
                    models.CharField(
                        blank=True,
                        help_text="ใช้กรณีอยากกรอกชื่อวิชาเอง หรือไม่มีใน Subject",
                        max_length=120,
                        verbose_name="วิชา / ชื่อวิชาแบบกรอกเอง",
                    ),
                ),
                ("topic", models.CharField(blank=True, max_length=255, verbose_name="เรื่อง")),
                (
                    "difficulty",
                    models.PositiveSmallIntegerField(
                        choices=[(1, "⭐"), (2, "⭐⭐"), (3, "⭐⭐⭐"), (4, "⭐⭐⭐⭐"), (5, "⭐⭐⭐⭐⭐")],
                        default=3,
                        verbose_name="ระดับความยาก",
                    ),
                ),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="weekly_tests_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="weekly_tests",
                        to="core.subject",
                        verbose_name="วิชาในระบบ",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="weekly_tests_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Weekly Small Test",
                "verbose_name_plural": "Weekly Small Tests",
                "ordering": ("-week_start", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="WeeklyTestScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attendance_date", models.DateField(blank=True, null=True, verbose_name="วันที่อ้างอิงจาก Dashboard")),
                (
                    "attendance_status",
                    models.CharField(
                        choices=[
                            ("present", "มา"),
                            ("excused", "ลา"),
                            ("no_show", "ขาด"),
                            ("not_checked", "ยังไม่เช็คชื่อ"),
                        ],
                        default="not_checked",
                        max_length=20,
                        verbose_name="สถานะจาก Dashboard",
                    ),
                ),
                (
                    "result",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("fail", "ไม่ผ่าน"),
                            ("medium", "ปานกลาง"),
                            ("good", "ดี"),
                            ("great", "ดีมาก"),
                            ("full", "เต็ม"),
                        ],
                        default="",
                        max_length=20,
                        verbose_name="ผล Test",
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="weekly_test_scores",
                        to="core.enrollment",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="weekly_test_scores",
                        to="core.student",
                    ),
                ),
                (
                    "tutoring_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="weekly_test_scores",
                        to="core.tutoringclass",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "weekly_test",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scores",
                        to="core.weeklytest",
                    ),
                ),
            ],
            options={
                "verbose_name": "Weekly Small Test Score",
                "verbose_name_plural": "Weekly Small Test Scores",
                "ordering": ("weekly_test", "tutoring_class__name", "student__nickname", "student__full_name"),
            },
        ),
        migrations.AddConstraint(
            model_name="weeklytest",
            constraint=models.UniqueConstraint(fields=("week_start",), name="uniq_weekly_test_per_week"),
        ),
        migrations.AddConstraint(
            model_name="weeklytestscore",
            constraint=models.UniqueConstraint(fields=("weekly_test", "enrollment"), name="uniq_weekly_test_score_per_enrollment"),
        ),
    ]
