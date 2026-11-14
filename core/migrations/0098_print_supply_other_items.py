from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0097_print_sides_default_double"),
    ]

    operations = [
        migrations.AlterField(
            model_name="printsupply",
            name="category",
            field=models.CharField(
                choices=[("cover_paper", "กระดาษปก"), ("a4_paper", "กระดาษ A4"), ("spine", "สันรูด"), ("ink", "หมึก"), ("drum", "Drum หมึก"), ("other", "สินค้าอื่นๆ")],
                max_length=20, verbose_name="ประเภท",
            ),
        ),
        migrations.RemoveConstraint(model_name="printsupply", name="uniq_print_supply"),
        migrations.AddConstraint(
            model_name="printsupply",
            constraint=models.UniqueConstraint(fields=("category", "spine_color", "spine_size", "name"), name="uniq_print_supply_v2"),
        ),
    ]
