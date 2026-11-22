from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0102_subject_template_next_sheet"),
    ]

    operations = [
        migrations.AddField(
            model_name="admintoolcard",
            name="size",
            field=models.CharField(default="m", help_text="s = เล็ก, m = กลาง, l = ใหญ่", max_length=1, verbose_name="ขนาดปุ่ม"),
        ),
    ]
