from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0092_print_supply_rules"),
    ]

    operations = [
        migrations.AddField(
            model_name="pretestapplication",
            name="filing_round",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="รอบที่ยื่น"),
        ),
        migrations.AddField(
            model_name="pretestapplication",
            name="filing_date",
            field=models.DateField(blank=True, null=True, verbose_name="วันที่ยื่น"),
        ),
    ]
