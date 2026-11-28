from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0105_renewal_notice_per_session"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollment", name="pay_after_class",
            field=models.BooleanField(default=False, verbose_name="คอร์สแบบจ่ายหลังเรียน",
                                      help_text="นักเรียนเรียนก่อนแล้วจ่ายทีหลัง -- ระบบจะนับว่าครบคอร์สเมื่อเรียนเกินไปแล้วตามจำนวนครั้งด้านล่าง"),
        ),
        migrations.AddField(
            model_name="enrollment", name="pay_after_sessions",
            field=models.PositiveIntegerField(default=10, verbose_name="จ่ายหลังเรียน: เรียนเกินได้กี่ครั้งก่อนครบคอร์ส",
                                              help_text="เช่น 10 = แจ้งต่อคอร์สเมื่อคงเหลือติดลบใกล้ -10"),
        ),
    ]
