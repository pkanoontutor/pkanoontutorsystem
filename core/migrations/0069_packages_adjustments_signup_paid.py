import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Course packages with installments, session adjustment slips, and the
    "paid at signup" flag on admission inquiries.

    Hand-written: the local venv runs Django 6.0 against a 4.2.16 pin, so
    autodetect output would carry unrelated pre-existing drift.
    """

    dependencies = [
        ("core", "0068_income_and_rate350"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="admissioninquiry",
            name="paid_on_signup",
            field=models.BooleanField(
                default=False,
                help_text="ติ๊กจากปุ่มในภาพรวม Admin Tool -- การ์ดยังอยู่ จนกว่าจะปิดเอง",
                verbose_name="สมัครและจ่ายเงินแล้ว",
            ),
        ),
        migrations.CreateModel(
            name="CoursePackage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("total_sessions", models.PositiveIntegerField(verbose_name="จำนวนครั้งทั้งแพ็กเกจ")),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="ยอดเต็มทั้งแพ็กเกจ")),
                ("installment_count", models.PositiveIntegerField(default=1, verbose_name="จำนวนงวด")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("enrollment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="packages", to="core.enrollment")),
            ],
            options={
                "verbose_name": "Course Package",
                "verbose_name_plural": "Course Packages",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="CoursePackageInstallment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("installment_no", models.PositiveIntegerField(verbose_name="งวดที่")),
                ("sessions", models.PositiveIntegerField(verbose_name="จำนวนครั้งของงวดนี้")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="ยอดงวดนี้")),
                ("due_date", models.DateField(blank=True, null=True, verbose_name="กำหนดชำระ")),
                ("package", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="installments", to="core.coursepackage")),
                ("receipt", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="package_installment", to="core.coursepayment")),
            ],
            options={
                "verbose_name": "Course Package Installment",
                "verbose_name_plural": "Course Package Installments",
                "ordering": ("package", "installment_no"),
            },
        ),
        migrations.AddConstraint(
            model_name="coursepackageinstallment",
            constraint=models.UniqueConstraint(fields=("package", "installment_no"), name="uniq_package_installment_no"),
        ),
        migrations.CreateModel(
            name="SessionAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delta", models.DecimalField(decimal_places=1, max_digits=5, verbose_name="ปรับเพิ่ม / ลด (ครั้ง)")),
                ("reason", models.TextField(verbose_name="เหตุผล")),
                ("remaining_before", models.DecimalField(decimal_places=1, max_digits=6, verbose_name="คงเหลือก่อนปรับ")),
                ("remaining_after", models.DecimalField(decimal_places=1, max_digits=6, verbose_name="คงเหลือหลังปรับ")),
                ("expected_end_before", models.DateField(blank=True, null=True, verbose_name="คาดว่าครบคอร์ส (ก่อน)")),
                ("expected_end_after", models.DateField(blank=True, null=True, verbose_name="คาดว่าครบคอร์ส (หลัง)")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="session_adjustments", to=settings.AUTH_USER_MODEL)),
                ("enrollment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="session_adjustments", to="core.enrollment")),
            ],
            options={
                "verbose_name": "Session Adjustment",
                "verbose_name_plural": "Session Adjustments",
                "ordering": ("-created_at",),
            },
        ),
    ]
