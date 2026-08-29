
# Generated manually for Pkanoon Tutor: editable online-teaching rate on a
# payroll entry (was a hardcoded 300 baht/hr).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0063_staged_sheet_document"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutorpayrollentry",
            name="online_hourly_rate",
            field=models.DecimalField(decimal_places=2, default=300, max_digits=10, verbose_name="เรทออนไลน์ต่อชั่วโมง"),
        ),
        migrations.AddField(
            model_name="tutorpayrollentry",
            name="online_hourly_rate_override",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True,
                help_text="เว้นว่างเพื่อใช้เรทออนไลน์เริ่มต้น 300 บาท/ชม. ใส่ตัวเลขเพื่อ override",
                verbose_name="เรทออนไลน์ที่กำหนดเอง",
            ),
        ),
    ]
