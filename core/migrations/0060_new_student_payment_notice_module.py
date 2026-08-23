
# Generated manually for Pkanoon Tutor new-student payment notice module

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0059_admintoolcard_tutor_sheets"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NewStudentPaymentNotice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nickname", models.CharField(blank=True, max_length=100, verbose_name="ชื่อเล่น")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="ชื่อจริง")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="นามสกุล")),
                ("school_name", models.CharField(blank=True, max_length=255, verbose_name="โรงเรียน")),
                ("contact_phone", models.CharField(blank=True, max_length=50, verbose_name="เบอร์ติดต่อ")),
                ("grade_level", models.CharField(blank=True, choices=[("p4", "ป.4"), ("p5", "ป.5"), ("p6", "ป.6"), ("m1", "ม.1"), ("m2", "ม.2"), ("m3", "ม.3"), ("m4", "ม.4")], max_length=20, verbose_name="ระดับชั้น")),
                ("first_lesson_date", models.DateField(blank=True, null=True, verbose_name="วันที่เริ่มเรียนวันแรก")),
                ("package_10_full_price", models.DecimalField(decimal_places=2, default=3990, max_digits=10, verbose_name="10 สัปดาห์ - ราคาเต็ม")),
                ("package_10_discount", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="10 สัปดาห์ - ส่วนลด")),
                ("package_10_net_price", models.DecimalField(decimal_places=2, default=3990, max_digits=10, verbose_name="10 สัปดาห์ - ราคาสุทธิ")),
                ("package_20_full_price", models.DecimalField(decimal_places=2, default=7980, max_digits=10, verbose_name="20 สัปดาห์ - ราคาเต็ม")),
                ("package_20_discount", models.DecimalField(decimal_places=2, default=300, max_digits=10, verbose_name="20 สัปดาห์ - ส่วนลด")),
                ("package_20_net_price", models.DecimalField(decimal_places=2, default=7680, max_digits=10, verbose_name="20 สัปดาห์ - ราคาสุทธิ")),
                ("package_30_full_price", models.DecimalField(decimal_places=2, default=11970, max_digits=10, verbose_name="30 สัปดาห์ - ราคาเต็ม")),
                ("package_30_discount", models.DecimalField(decimal_places=2, default=800, max_digits=10, verbose_name="30 สัปดาห์ - ส่วนลด")),
                ("package_30_net_price", models.DecimalField(decimal_places=2, default=11170, max_digits=10, verbose_name="30 สัปดาห์ - ราคาสุทธิ")),
                ("note_wording", models.TextField(default="ชำระแล้วรบกวนส่งสลิปแจ้งพี่ขนุนทาง Line @ เพื่อยืนยันที่นั่งและออกใบเสร็จให้ครับ", verbose_name="ข้อความท้ายใบแจ้ง")),
                ("is_sent_to_parent", models.BooleanField(default=False, verbose_name="ส่งแจ้งผู้ปกครองแล้ว")),
                ("sent_to_parent_at", models.DateTimeField(blank=True, null=True, verbose_name="วันที่ส่งแจ้งผู้ปกครอง")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("admission_inquiry", models.ForeignKey(blank=True, help_text="ใบสมัครที่ใช้ดึงข้อมูลมาตอนสร้าง (ไม่ผูกติดกัน แก้ไขในใบแจ้งนี้ได้อิสระ)", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="new_student_payment_notices", to="core.admissioninquiry", verbose_name="ใบสมัครอ้างอิง")),
                ("target_class", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="new_student_payment_notices", to="core.tutoringclass", verbose_name="Class ที่คาดว่าจะเข้าเรียน")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_new_student_payment_notices", to=settings.AUTH_USER_MODEL, verbose_name="ผู้สร้าง")),
                ("sent_to_parent_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sent_new_student_payment_notices", to=settings.AUTH_USER_MODEL, verbose_name="ผู้กดส่งแจ้ง")),
            ],
            options={
                "verbose_name": "New Student Payment Notice",
                "verbose_name_plural": "New Student Payment Notices",
                "ordering": ("-created_at",),
            },
        ),
    ]
