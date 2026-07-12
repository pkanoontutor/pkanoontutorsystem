# Generated manually for P'Kanoon Tutor
from django.db import migrations, models
import django.db.models.deletion

# Slightly darker room-header tones (old -> new); customised colours untouched.
_HEADER_COLOR_MAP = {
    "#fbf2b0": "#f6e88a",
    "#eadaf0": "#dfc6ea",
    "#d9ebc6": "#c6e2a8",
    "#f8d3d9": "#f5bcc7",
    "#dad1c5": "#cbbfae",
}

# Fruit icon per default room name (no exact durian/mangosteen emoji exists;
# nearest look-alikes used — editable per room in admin).
_ROOM_ICONS = {
    "ห้องทุเรียนหมอนทอง": "🍈",
    "ห้องมังคุดคัด": "🍇",
    "ห้องมะม่วงเขียวเสวย": "🥭",
    "ห้องแตงโมจินตหรา": "🍉",
    "ห้องมะพร้าว": "🥥",
}


def forwards(apps, schema_editor):
    ScheduleRoom = apps.get_model("core", "ScheduleRoom")
    TeachingTutor = apps.get_model("core", "TeachingTutor")
    Tutor = apps.get_model("core", "Tutor")

    # 1) Rename the watermelon room per the reference image.
    ScheduleRoom.objects.filter(name="ห้องแตงโมอินทรา").update(name="ห้องแตงโมจินตหรา")

    # 2) Darken default header colours.
    for old, new in _HEADER_COLOR_MAP.items():
        ScheduleRoom.objects.filter(header_color=old).update(header_color=new)

    # 3) Seed fruit icons for rooms that don't have one yet.
    for room in ScheduleRoom.objects.filter(icon=""):
        icon = _ROOM_ICONS.get(room.name)
        if icon:
            room.icon = icon
            room.save(update_fields=["icon"])

    # 4) Auto-match teaching tutors to payroll tutors by exact name.
    payroll_by_name = {t.name.strip(): t for t in Tutor.objects.all()}
    for tt in TeachingTutor.objects.filter(payroll_tutor__isnull=True):
        match = payroll_by_name.get(tt.name.strip())
        if match:
            tt.payroll_tutor = match
            tt.save(update_fields=["payroll_tutor"])


def backwards(apps, schema_editor):
    ScheduleRoom = apps.get_model("core", "ScheduleRoom")
    ScheduleRoom.objects.filter(name="ห้องแตงโมจินตหรา").update(name="ห้องแตงโมอินทรา")
    for old, new in _HEADER_COLOR_MAP.items():
        ScheduleRoom.objects.filter(header_color=new).update(header_color=old)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0034_schedule_room_colors"),
    ]

    operations = [
        migrations.AddField(
            model_name="scheduleroom",
            name="icon",
            field=models.CharField(blank=True, default="", max_length=16, verbose_name="ไอคอนผลไม้ (emoji)"),
        ),
        migrations.AddField(
            model_name="teachingtutor",
            name="payroll_tutor",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="teaching_profiles", to="core.tutor", verbose_name="ผูกกับติวเตอร์ในระบบเงิน (รายจ่าย/ค่าสอน)"),
        ),
        migrations.RunPython(forwards, backwards),
    ]
