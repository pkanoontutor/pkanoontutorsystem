from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0096_spine_color_yellow"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sheetprintorder",
            name="print_sides",
            field=models.CharField(choices=[("single", "ด้านเดียว"), ("double", "หน้าหลัง")], default="double", max_length=10, verbose_name="การปรินท์"),
        ),
    ]
