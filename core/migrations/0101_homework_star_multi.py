from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0100_renewal_note_line_id"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="homeworkstar",
            name="uniq_homework_star_per_lesson",
        ),
    ]
