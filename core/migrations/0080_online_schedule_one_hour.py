from django.db import migrations


def reset_hours(apps, schema_editor):
    # Online lessons always pay 1 hour each; some weeks had this set to 5.
    apps.get_model("core", "OnlineSchedule").objects.exclude(hours_per_session=1).update(hours_per_session=1)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0079_subadmintool"),
    ]

    operations = [
        migrations.RunPython(reset_hours, migrations.RunPython.noop),
    ]
