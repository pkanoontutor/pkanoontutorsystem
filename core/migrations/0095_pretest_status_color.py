from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0094_pretest_round"),
    ]

    operations = [
        migrations.CreateModel(
            name="PretestStatusColor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(max_length=20, unique=True, verbose_name="สถานะ")),
                ("color", models.CharField(max_length=7, verbose_name="สี")),
            ],
        ),
    ]
