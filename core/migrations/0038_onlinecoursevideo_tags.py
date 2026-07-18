# Generated manually for P'Kanoon Tutor
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0037_admintoolcard_online_course_videos"),
    ]

    operations = [
        migrations.AddField(
            model_name="onlinecoursevideo",
            name="subject_tag",
            field=models.CharField(blank=True, max_length=100, verbose_name="วิชา"),
        ),
        migrations.AddField(
            model_name="onlinecoursevideo",
            name="tutor_name",
            field=models.CharField(blank=True, max_length=120, verbose_name="ชื่อติวเตอร์"),
        ),
        migrations.AddField(
            model_name="onlinecoursevideo",
            name="duration_minutes",
            field=models.PositiveIntegerField(default=0, help_text="ใช้สำหรับ auto play คลิปถัดไปเมื่อคลิปนี้จบ (0 = ไม่ทราบ ระบบจะไม่ auto ต่อ)", verbose_name="ความยาวคลิป (นาที)"),
        ),
    ]
