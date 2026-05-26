
# Generated manually for Pkanoon Tutor course renewal notice module

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_admission_inquiry_completed_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseRenewalNotice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expected_course_end_date", models.DateField(verbose_name="วันที่คาดว่าจะครบคอร์ส")),
                ("next_course_start_date", models.DateField(verbose_name="วันที่เริ่มต้นคอร์สใหม่")),
                ("package_10_full_price", models.DecimalField(decimal_places=2, default=3990, max_digits=10, verbose_name="10 สัปดาห์ - ราคาเต็ม")),
                ("package_10_discount", models.DecimalField(decimal_places=2, default=100, max_digits=10, verbose_name="10 สัปดาห์ - ส่วนลด")),
                ("package_10_net_price", models.DecimalField(decimal_places=2, default=3890, max_digits=10, verbose_name="10 สัปดาห์ - ราคาสุทธิ")),
                ("package_20_full_price", models.DecimalField(decimal_places=2, default=7980, max_digits=10, verbose_name="20 สัปดาห์ - ราคาเต็ม")),
                ("package_20_discount", models.DecimalField(decimal_places=2, default=500, max_digits=10, verbose_name="20 สัปดาห์ - ส่วนลด")),
                ("package_20_net_price", models.DecimalField(decimal_places=2, default=7480, max_digits=10, verbose_name="20 สัปดาห์ - ราคาสุทธิ")),
                ("package_30_full_price", models.DecimalField(decimal_places=2, default=11970, max_digits=10, verbose_name="30 สัปดาห์ - ราคาเต็ม")),
                ("package_30_discount", models.DecimalField(decimal_places=2, default=1000, max_digits=10, verbose_name="30 สัปดาห์ - ส่วนลด")),
                ("package_30_net_price", models.DecimalField(decimal_places=2, default=10970, max_digits=10, verbose_name="30 สัปดาห์ - ราคาสุทธิ")),
                ("note_wording", models.TextField(default="ผู้ปกครองสามารถขอชะลอจ่าย เลื่อนจ่ายเป็นสิ้นเดือนได้โดยนักเรียนไม่ต้องเว้นวรรคการเรียนครับ ติดต่อแจ้งพี่ขนุนทาง Line @ ครับ", verbose_name="ข้อความท้ายใบแจ้ง")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_course_renewal_notices", to=settings.AUTH_USER_MODEL, verbose_name="ผู้สร้าง")),
                ("enrollment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="renewal_notices", to="core.enrollment", verbose_name="Enrollment")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="renewal_notices", to="core.student", verbose_name="นักเรียน")),
                ("tutoring_class", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="renewal_notices", to="core.tutoringclass", verbose_name="คอร์ส/คลาส")),
            ],
            options={
                "verbose_name": "Course Renewal Notice",
                "verbose_name_plural": "Course Renewal Notices",
                "ordering": ("-created_at",),
            },
        ),
    ]
