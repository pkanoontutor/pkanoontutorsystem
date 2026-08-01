from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0045_course_payment_other_receipts"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutorpayrollentry",
            name="hourly_rate_override",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="เว้นว่างเพื่อใช้เรทเริ่มต้นตามชั่วโมงสอน/เรทพิเศษ 325 โดยอัตโนมัติ ใส่ตัวเลขเพื่อ override",
                max_digits=10,
                null=True,
                verbose_name="เรทค่าสอนที่กำหนดเอง",
            ),
        ),
        migrations.AddField(
            model_name="tutorpayrollentry",
            name="travel_fee_override",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="เว้นว่างเพื่อใช้ค่าเดินทางเริ่มต้นตามชั่วโมงสอนโดยอัตโนมัติ ใส่ตัวเลขเพื่อ override",
                max_digits=12,
                null=True,
                verbose_name="ค่าเดินทางที่กำหนดเอง",
            ),
        ),
    ]
