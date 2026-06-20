# Generated manually for print order receiving workflow
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0027_teaching_update_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="sheetprintorder",
            name="received_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="วันที่ตรวจรับเข้าคลัง"),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="received_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="received_sheet_print_orders", to=settings.AUTH_USER_MODEL, verbose_name="ผู้ตรวจรับ"),
        ),
        migrations.AlterField(
            model_name="sheetprintorder",
            name="status",
            field=models.CharField(choices=[("pending", "รอปรินท์"), ("ready", "ปรินท์เสร็จแล้วพร้อมส่ง"), ("received", "ตรวจรับเข้าคลังแล้ว")], default="pending", max_length=20, verbose_name="สถานะ"),
        ),
    ]
