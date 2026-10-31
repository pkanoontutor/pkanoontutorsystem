import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0086_home_budget_floors"),
    ]

    operations = [
        migrations.AddField(model_name="newstudentpaymentnotice", name="student",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="new_student_payment_notices", to="core.student", verbose_name="นักเรียนเดิมที่ดึงข้อมูลมา")),
        migrations.AddField(model_name="newstudentpaymentnotice", name="price_mode",
            field=models.CharField(choices=[("packages", "แพ็กเกจ 10 / 20 / 30"), ("custom", "กำหนดคอร์สและราคาเอง")], default="packages", max_length=10, verbose_name="รูปแบบราคา")),
        migrations.AddField(model_name="newstudentpaymentnotice", name="custom_course_name",
            field=models.CharField(blank=True, max_length=255, verbose_name="ชื่อคอร์ส (กำหนดเอง)")),
        migrations.AddField(model_name="newstudentpaymentnotice", name="custom_full_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="ราคาเต็ม (กำหนดเอง)")),
        migrations.AddField(model_name="newstudentpaymentnotice", name="custom_discount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="ส่วนลด (กำหนดเอง)")),
        migrations.AddField(model_name="newstudentpaymentnotice", name="custom_net_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="ราคาสุทธิ (กำหนดเอง)")),
    ]
