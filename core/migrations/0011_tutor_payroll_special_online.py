from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_school_finance_modules"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutorpayrollentry",
            name="special_rate_325",
            field=models.BooleanField(
                default=False,
                help_text="ติ๊กเฉพาะติวเตอร์ที่ได้เรทพิเศษ กรณีสอน onsite ตั้งแต่ 4 ชั่วโมงขึ้นไป",
                verbose_name="ใช้อัตราพิเศษ 325 บาท/ชม. เมื่อสอนตั้งแต่ 4 ชม.",
            ),
        ),
        migrations.AddField(
            model_name="tutorpayrollentry",
            name="online_teaching_hours",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=5,
                verbose_name="จำนวนชั่วโมงสอนออนไลน์",
            ),
        ),
        migrations.AddField(
            model_name="tutorpayrollentry",
            name="online_teaching_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                verbose_name="ค่าสอนออนไลน์",
            ),
        ),
    ]
