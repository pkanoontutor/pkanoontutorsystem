from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0095_pretest_status_color"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sheetprintorder",
            name="spine_color",
            field=models.CharField(
                blank=True,
                choices=[("blue", "สีฟ้า"), ("red", "สีแดง"), ("pink", "สีชมพู"), ("green", "สีเขียว"), ("orange", "สีส้ม"), ("yellow", "สีเหลือง")],
                default="",
                help_text="ใช้เฉพาะกรณีเย็บข้าง",
                max_length=20,
                verbose_name="สีสันรูด",
            ),
        ),
    ]
