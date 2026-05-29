# Generated for PKanoon Tutor sheet print order module
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0019_sheet_inventory_scanner_module"),
    ]

    operations = [
        migrations.AddField(
            model_name="sheetinventory",
            name="target_stock",
            field=models.PositiveIntegerField(default=0, help_text="ใช้คำนวณจำนวนที่ควรสั่งปรินท์เพิ่ม", verbose_name="จำนวนที่ต้องการมีในคลัง"),
        ),
        migrations.AddField(
            model_name="sheetinventory",
            name="onedrive_url",
            field=models.URLField(blank=True, help_text="ลิงก์ไฟล์ชีทสำหรับส่งร้านปรินท์", max_length=1000, verbose_name="ลิงก์ไฟล์ OneDrive"),
        ),
        migrations.CreateModel(
            name="SheetPrintOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1, verbose_name="จำนวนที่สั่งปรินท์")),
                ("due_date", models.DateField(blank=True, null=True, verbose_name="วันที่ต้องส่ง")),
                ("onedrive_url", models.URLField(blank=True, max_length=1000, verbose_name="ลิงก์ไฟล์ OneDrive")),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("status", models.CharField(choices=[("pending", "รอปรินท์"), ("ready", "ปรินท์เสร็จแล้วพร้อมส่ง")], default="pending", max_length=20, verbose_name="สถานะ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สั่ง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("completed_at", models.DateTimeField(blank=True, null=True, verbose_name="วันที่ร้านกดเสร็จแล้ว")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sheet_print_orders", to=settings.AUTH_USER_MODEL, verbose_name="ผู้สั่งปรินท์")),
                ("sheet", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="print_orders", to="core.sheet", verbose_name="ชีท")),
            ],
            options={
                "verbose_name": "Sheet Print Order",
                "verbose_name_plural": "Sheet Print Orders",
                "ordering": ("status", "due_date", "created_at"),
            },
        ),
    ]
