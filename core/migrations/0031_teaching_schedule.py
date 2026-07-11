# Generated manually for P'Kanoon Tutor
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0030_admintoolcard"),
    ]

    operations = [
        migrations.AddField(
            model_name="teachingtutor",
            name="color",
            field=models.CharField(default="#1d4ed8", max_length=20, verbose_name="สีประจำตัว (ใช้บนตารางเรียน)"),
        ),
        migrations.CreateModel(
            name="ScheduleRoom",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="ชื่อห้อง")),
                ("header_color", models.CharField(default="#fdf3bf", max_length=20, verbose_name="สีหัวคอลัมน์")),
                ("display_order", models.PositiveIntegerField(default=1, verbose_name="ลำดับคอลัมน์")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("default_class", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="default_schedule_rooms", to="core.tutoringclass", verbose_name="ผูกกับคลาส (ไม่แสดงชื่อ)")),
            ],
            options={
                "verbose_name": "Schedule Room",
                "verbose_name_plural": "Schedule Rooms",
                "ordering": ("display_order", "id"),
            },
        ),
        migrations.CreateModel(
            name="ScheduleExamCountdown",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("grade_label", models.CharField(max_length=40, verbose_name="ระดับชั้น")),
                ("exam_date", models.DateField(verbose_name="วันสอบ")),
                ("note", models.CharField(blank=True, max_length=120, verbose_name="หมายเหตุ (เช่น รอบแรก - ห้องพิเศษ)")),
                ("display_order", models.PositiveIntegerField(default=1, verbose_name="ลำดับ")),
                ("is_active", models.BooleanField(default=True, verbose_name="แสดงบนตาราง")),
            ],
            options={
                "verbose_name": "Schedule Exam Countdown",
                "verbose_name_plural": "Schedule Exam Countdowns",
                "ordering": ("display_order", "exam_date", "id"),
            },
        ),
        migrations.CreateModel(
            name="DailySchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(unique=True, verbose_name="วันที่")),
                ("title_note", models.CharField(blank=True, max_length=200, verbose_name="ข้อความหัวเรื่องเพิ่มเติม")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Daily Schedule",
                "verbose_name_plural": "Daily Schedules",
                "ordering": ("-date",),
            },
        ),
        migrations.CreateModel(
            name="DailyScheduleCell",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("time_index", models.PositiveIntegerField(verbose_name="ลำดับคาบ")),
                ("grade_label", models.CharField(blank=True, max_length=40, verbose_name="ระดับชั้น")),
                ("subject_label", models.CharField(blank=True, max_length=120, verbose_name="วิชา")),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cells", to="core.scheduleroom")),
                ("schedule", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cells", to="core.dailyschedule")),
                ("subject_template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="schedule_cells", to="core.teachingclasssubjecttemplate")),
                ("tutor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="schedule_cells", to="core.teachingtutor")),
                ("tutoring_class", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="schedule_cells", to="core.tutoringclass")),
            ],
            options={
                "verbose_name": "Daily Schedule Cell",
                "verbose_name_plural": "Daily Schedule Cells",
                "ordering": ("time_index", "room__display_order"),
            },
        ),
        migrations.AddConstraint(
            model_name="dailyschedulecell",
            constraint=models.UniqueConstraint(fields=["schedule", "room", "time_index"], name="uniq_schedule_cell"),
        ),
    ]
