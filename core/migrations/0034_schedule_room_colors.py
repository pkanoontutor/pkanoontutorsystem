# Generated manually for P'Kanoon Tutor
from django.db import migrations

# Update rooms that still carry the previous seed colours to the tones sampled
# from the reference schedule image. Custom colours are left untouched.
_COLOR_MAP = {
    "#fdf3bf": "#fbf2b0",
    "#efe1f5": "#eadaf0",
    "#dcefc9": "#d9ebc6",
    "#f8d7de": "#f8d3d9",
    "#ddd6ca": "#dad1c5",
}


def apply_colors(apps, schema_editor):
    ScheduleRoom = apps.get_model("core", "ScheduleRoom")
    for old, new in _COLOR_MAP.items():
        ScheduleRoom.objects.filter(header_color=old).update(header_color=new)


def revert_colors(apps, schema_editor):
    ScheduleRoom = apps.get_model("core", "ScheduleRoom")
    for old, new in _COLOR_MAP.items():
        ScheduleRoom.objects.filter(header_color=new).update(header_color=old)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0033_scheduleroom_satsun_classes"),
    ]

    operations = [
        migrations.RunPython(apply_colors, revert_colors),
    ]
