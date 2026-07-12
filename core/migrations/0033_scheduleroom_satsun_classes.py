# Generated manually for P'Kanoon Tutor
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0032_scheduleroom_halfday_classes"),
    ]

    operations = [
        # Carry the existing morning/afternoon binding over to Saturday
        # (the default schedule day) before renaming the fields.
        migrations.RenameField(
            model_name="scheduleroom",
            old_name="morning_class",
            new_name="sat_morning_class",
        ),
        migrations.RenameField(
            model_name="scheduleroom",
            old_name="afternoon_class",
            new_name="sat_afternoon_class",
        ),
        migrations.AlterField(
            model_name="scheduleroom",
            name="sat_morning_class",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sat_morning_schedule_rooms", to="core.tutoringclass", verbose_name="เสาร์เช้า (08.30-12.30)"),
        ),
        migrations.AlterField(
            model_name="scheduleroom",
            name="sat_afternoon_class",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sat_afternoon_schedule_rooms", to="core.tutoringclass", verbose_name="เสาร์บ่าย (13.30-17.30)"),
        ),
        migrations.AddField(
            model_name="scheduleroom",
            name="sun_morning_class",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sun_morning_schedule_rooms", to="core.tutoringclass", verbose_name="อาทิตย์เช้า (08.30-12.30)"),
        ),
        migrations.AddField(
            model_name="scheduleroom",
            name="sun_afternoon_class",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sun_afternoon_schedule_rooms", to="core.tutoringclass", verbose_name="อาทิตย์บ่าย (13.30-17.30)"),
        ),
    ]
