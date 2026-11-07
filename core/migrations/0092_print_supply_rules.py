from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0091_print_supplies"),
    ]

    operations = [
        migrations.RemoveField(model_name="printsupply", name="low_threshold"),
    ]
