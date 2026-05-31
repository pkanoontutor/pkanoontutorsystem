# Generated manually for Pkanoon Tutor system
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_test_score_announcement_module"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sheetprintorder",
            name="sheet",
            field=models.ForeignKey(
                blank=True,
                help_text="เว้นว่างได้สำหรับรายการเอกสารอื่นที่ไม่ใช่ชีทใน Sheet Inventory",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="print_orders",
                to="core.sheet",
                verbose_name="ชีท",
            ),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="custom_title",
            field=models.CharField(
                blank=True,
                help_text="ใช้กรณีสั่งปรินท์เอกสารที่ไม่ได้อยู่ใน Sheet Inventory",
                max_length=255,
                verbose_name="ชื่อเอกสารอื่น",
            ),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="binding_type",
            field=models.CharField(
                choices=[("corner", "เย็บมุม"), ("side", "เย็บข้าง")],
                default="side",
                max_length=20,
                verbose_name="ประเภทการเย็บ",
            ),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="spine_color",
            field=models.CharField(
                blank=True,
                choices=[
                    ("blue", "สีฟ้า"),
                    ("red", "สีแดง"),
                    ("pink", "สีชมพู"),
                    ("green", "สีเขียว"),
                    ("orange", "สีส้ม"),
                ],
                default="",
                help_text="ใช้เฉพาะกรณีเย็บข้าง",
                max_length=20,
                verbose_name="สีสันรูด",
            ),
        ),
    ]
