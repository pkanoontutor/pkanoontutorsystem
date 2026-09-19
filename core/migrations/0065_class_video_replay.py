import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    """Class video replay: session (class+date) -> 4 clips -> per-student watch log.

    Hand-written rather than makemigrations output: the local venv runs
    Django 6.0 while production pins 4.2.16, and autodetect also wanted to
    replay unrelated pre-existing drift (recreating School, altering many
    fields) that must not run against the live database.
    """

    dependencies = [
        ("core", "0064_tutor_payroll_online_rate"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassVideoSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lesson_date", models.DateField(verbose_name="วันที่เรียน")),
                ("is_published", models.BooleanField(default=False, help_text="ติ๊กเมื่อใส่ลิงก์ครบแล้ว ถ้ายังไม่ติ๊กผู้ปกครองจะไม่เห็นวันนี้", verbose_name="เผยแพร่ให้ผู้ปกครองดู")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tutoring_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="video_sessions", to="core.tutoringclass", verbose_name="คลาส")),
            ],
            options={
                "verbose_name": "Class Video Session",
                "verbose_name_plural": "Class Video Sessions",
                "ordering": ("-lesson_date", "tutoring_class__name"),
            },
        ),
        migrations.CreateModel(
            name="ClassVideoClip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slot_index", models.PositiveIntegerField(default=1, verbose_name="คาบที่ (1-4)")),
                ("time_index", models.PositiveIntegerField(default=0, help_text="index ของ TEACHING_SCHEDULE_SLOTS ใช้จับคู่กับตารางสอน", verbose_name="ลำดับคาบในตารางสอน")),
                ("video_url", models.URLField(blank=True, max_length=500, verbose_name="ลิงก์ YouTube")),
                ("subject_label", models.CharField(blank=True, max_length=120, verbose_name="วิชา")),
                ("schedule_subject", models.CharField(blank=True, max_length=120, verbose_name="วิชาตามตารางสอน")),
                ("schedule_tutor_name", models.CharField(blank=True, max_length=120, verbose_name="ติวเตอร์ตามตารางสอน")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="clips", to="core.classvideosession")),
                ("tutor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="video_clips", to="core.teachingtutor", verbose_name="ติวเตอร์")),
            ],
            options={
                "verbose_name": "Class Video Clip",
                "verbose_name_plural": "Class Video Clips",
                "ordering": ("session", "slot_index"),
            },
        ),
        migrations.CreateModel(
            name="ClassVideoWatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("first_watched_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="ดูครั้งแรก")),
                ("last_watched_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="ดูล่าสุด")),
                ("watch_count", models.PositiveIntegerField(default=1, verbose_name="จำนวนครั้งที่เปิด")),
                ("clip", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="watches", to="core.classvideoclip")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="video_watches", to="core.student")),
            ],
            options={
                "verbose_name": "Class Video Watch",
                "verbose_name_plural": "Class Video Watches",
                "ordering": ("-last_watched_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="classvideosession",
            constraint=models.UniqueConstraint(fields=("tutoring_class", "lesson_date"), name="uniq_class_video_session_per_class_date"),
        ),
        migrations.AddConstraint(
            model_name="classvideoclip",
            constraint=models.UniqueConstraint(fields=("session", "slot_index"), name="uniq_class_video_clip_per_slot"),
        ),
        migrations.AddConstraint(
            model_name="classvideowatch",
            constraint=models.UniqueConstraint(fields=("student", "clip"), name="uniq_class_video_watch_per_student_clip"),
        ),
    ]
