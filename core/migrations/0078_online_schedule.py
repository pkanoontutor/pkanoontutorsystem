import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

_URL = "/online-schedule/"


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if AdminToolCard.objects.filter(url=_URL).exists():
        return
    max_order = (
        AdminToolCard.objects.filter(section="private")
        .order_by("-order").values_list("order", flat=True).first()
    ) or 0
    AdminToolCard.objects.create(
        section="private", icon="💻", name="ตารางเรียน Online",
        desc="สร้างปฏิทินตารางเรียนออนไลน์รายสัปดาห์เป็นรูป แล้วส่งค่าติวเตอร์ (ชม.ละ 300 + ติวเตอร์เฉลยเทส +2 ชม.) เข้าระบบรายรับรายจ่าย",
        url=_URL, color="c-lilac", order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    apps.get_model("core", "AdminToolCard").objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0077_snackshopentry"),
    ]

    operations = [
        migrations.CreateModel(
            name="OnlineSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField(verbose_name="วันที่เริ่ม")),
                ("end_date", models.DateField(verbose_name="วันที่สิ้นสุด")),
                ("time_text", models.CharField(default="19.00-20.00น.", max_length=60, verbose_name="เวลาเรียน")),
                ("hours_per_session", models.DecimalField(decimal_places=2, default=1, max_digits=4, verbose_name="ชั่วโมงต่อคาบ")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุใต้ตาราง")),
                ("payroll_sent_at", models.DateTimeField(blank=True, null=True, verbose_name="ส่งค่าติวเตอร์ล่าสุด")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Online Schedule", "verbose_name_plural": "Online Schedules", "ordering": ("-start_date",)},
        ),
        migrations.CreateModel(
            name="OnlineScheduleRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("grade_label", models.CharField(max_length=40, verbose_name="ระดับชั้น")),
                ("lesson_date", models.DateField(verbose_name="วันที่เรียน")),
                ("subject", models.CharField(max_length=120, verbose_name="วิชา")),
                ("sheet_code", models.CharField(blank=True, max_length=80, verbose_name="รหัสชีท")),
                ("order", models.PositiveIntegerField(default=0)),
                ("schedule", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rows", to="core.onlineschedule")),
                ("tutor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="online_rows", to="core.teachingtutor")),
            ],
            options={"ordering": ("order", "lesson_date", "id")},
        ),
        migrations.CreateModel(
            name="OnlineScheduleTestTutor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("work_date", models.DateField(verbose_name="วันที่เฉลยเทส")),
                ("hours", models.DecimalField(decimal_places=2, default=2, max_digits=4, verbose_name="ชั่วโมงที่ได้")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ")),
                ("schedule", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="test_tutors", to="core.onlineschedule")),
                ("tutor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="online_test_duties", to="core.teachingtutor")),
            ],
            options={"ordering": ("work_date", "id")},
        ),
        migrations.RunPython(add_card, remove_card),
    ]
