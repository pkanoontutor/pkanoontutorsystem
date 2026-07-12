# Generated manually for P'Kanoon Tutor
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0031_teaching_schedule"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="scheduleroom",
            name="default_class",
        ),
        migrations.AddField(
            model_name="scheduleroom",
            name="morning_class",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="morning_schedule_rooms", to="core.tutoringclass", verbose_name="คลาสรอบเช้า (08.30-12.30)"),
        ),
        migrations.AddField(
            model_name="scheduleroom",
            name="afternoon_class",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="afternoon_schedule_rooms", to="core.tutoringclass", verbose_name="คลาสรอบบ่าย (13.30-17.30)"),
        ),
    ]
