# Generated manually to skip migration number 0007

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_sheetinventory"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdmissionInquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_type", models.CharField(choices=[("trial", "จองทดลองเรียน"), ("enroll", "สมัครเรียน")], default="trial", max_length=20, verbose_name="ประเภทการลงทะเบียน")),
                ("nickname", models.CharField(max_length=100, verbose_name="ชื่อเล่น")),
                ("first_name", models.CharField(max_length=150, verbose_name="ชื่อจริง")),
                ("last_name", models.CharField(max_length=150, verbose_name="นามสกุล")),
                ("school_name", models.CharField(blank=True, max_length=255, verbose_name="โรงเรียน")),
                ("contact_phone", models.CharField(max_length=50, verbose_name="เบอร์ติดต่อ")),
                ("latest_gpa", models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name="เกรดเฉลี่ยเทอมล่าสุด")),
                ("first_lesson_date", models.DateField(verbose_name="วันที่ทดลองเรียน/เริ่มเรียนวันแรก")),
                ("grade_level", models.CharField(choices=[("kg", "อนุบาล"), ("p1", "ป.1"), ("p2", "ป.2"), ("p3", "ป.3"), ("p4", "ป.4"), ("p5", "ป.5"), ("p6", "ป.6"), ("m1", "ม.1"), ("m2", "ม.2"), ("m3", "ม.3"), ("m4", "ม.4"), ("m5", "ม.5"), ("m6", "ม.6"), ("other", "อื่น ๆ")], max_length=20, verbose_name="ระดับชั้น")),
                ("preferred_time_slot", models.CharField(choices=[("sat_morning", "เสาร์เช้า (08.30-12.30)"), ("sat_afternoon", "เสาร์บ่าย (13.30-17.30)"), ("sun_morning", "อาทิตย์เช้า (08.30-12.30)"), ("sun_afternoon", "อาทิตย์บ่าย (13.30-17.30)")], max_length=30, verbose_name="รอบเวลาเรียน")),
                ("sheet_prepared", models.BooleanField(default=False, verbose_name="เตรียมชีทพร้อมแล้ว")),
                ("trial_attended", models.CharField(choices=[("pending", "ยังไม่ระบุ"), ("yes", "มาเรียนจริง"), ("no", "ไม่ได้มาเรียน")], default="pending", help_text="ใช้สำหรับรายการจองทดลองเรียน", max_length=20, verbose_name="มาเรียนจริงหรือไม่")),
                ("trial_result", models.CharField(choices=[("pending", "ยังไม่ระบุ"), ("enrolled", "ทดลองแล้วสมัครต่อ"), ("not_enrolled", "ทดลองแล้วไม่สมัคร"), ("follow_up", "รอติดตามผล")], default="pending", help_text="ใช้สำหรับรายการจองทดลองเรียน", max_length=20, verbose_name="ผลหลังทดลองเรียน")),
                ("internal_note", models.TextField(blank=True, verbose_name="หมายเหตุภายใน")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่ลงทะเบียน")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
            ],
            options={
                "verbose_name": "Admission Inquiry",
                "verbose_name_plural": "Admission Inquiries",
                "ordering": ("-created_at",),
            },
        ),
    ]
