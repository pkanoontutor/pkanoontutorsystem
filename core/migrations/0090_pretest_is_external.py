from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0089_pretest_form_pdf"),
    ]

    operations = [
        migrations.AddField(
            model_name="pretestapplication",
            name="is_external",
            field=models.BooleanField(default=False, verbose_name="ไม่ใช่นักเรียนปัจจุบัน"),
        ),
    ]
