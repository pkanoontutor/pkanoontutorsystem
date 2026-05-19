from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


def seed_finance_defaults(apps, schema_editor):
    FinanceSetting = apps.get_model("core", "FinanceSetting")
    ExpenseCategory = apps.get_model("core", "ExpenseCategory")

    FinanceSetting.objects.get_or_create(
        key="revenue_per_student_per_week",
        defaults={
            "value": Decimal("360.00"),
            "description": "รายได้ประมาณการต่อคนต่อสัปดาห์ / ต่อครั้งที่หักชั่วโมง",
        },
    )
    FinanceSetting.objects.get_or_create(
        key="estimated_tutor_cost_per_class_per_week",
        defaults={
            "value": Decimal("1350.00"),
            "description": "ค่าใช้จ่ายติวเตอร์ประมาณการต่อ class ต่อสัปดาห์",
        },
    )

    categories = [
        ("ค่าจ้างติวเตอร์", True),
        ("ค่าเช่าสถานที่ / ห้องเรียน", False),
        ("ค่าน้ำ / ค่าไฟ", False),
        ("ค่าอินเทอร์เน็ต / โทรศัพท์", False),
        ("ค่าชีท / เอกสารประกอบการเรียน", False),
        ("ค่าปริ้นท์ / หมึก / กระดาษ", False),
        ("ค่าอุปกรณ์การเรียน", False),
        ("ค่าหนังสือ / แบบฝึกหัด", False),
        ("ค่าขนม / น้ำดื่มนักเรียน", False),
        ("ค่าโฆษณา / การตลาด", False),
        ("ค่าแพลตฟอร์มออนไลน์ / Software", False),
        ("ค่าธรรมเนียมธนาคาร / Payment", False),
        ("ค่าทำความสะอาด", False),
        ("ค่าซ่อมบำรุง", False),
        ("ค่าเดินทาง", False),
        ("ค่าใช้จ่ายอื่น ๆ", False),
    ]
    for idx, (name, is_tutor) in enumerate(categories, start=1):
        ExpenseCategory.objects.get_or_create(
            name=name,
            defaults={"is_tutor_payroll": is_tutor, "is_active": True, "sort_order": idx},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_admissioninquiry"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinanceSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=80, unique=True, verbose_name="Key")),
                ("value", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="Value")),
                ("description", models.CharField(blank=True, max_length=255, verbose_name="Description")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated at")),
            ],
            options={
                "verbose_name": "Finance Setting",
                "verbose_name_plural": "Finance Settings",
                "ordering": ("key",),
            },
        ),
        migrations.CreateModel(
            name="ExpenseCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="ประเภทค่าใช้จ่าย")),
                ("is_tutor_payroll", models.BooleanField(default=False, verbose_name="เป็นค่าจ้างติวเตอร์")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="ลำดับ")),
            ],
            options={
                "verbose_name": "Expense Category",
                "verbose_name_plural": "Expense Categories",
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="Tutor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="ชื่อติวเตอร์")),
                ("phone", models.CharField(blank=True, max_length=50, verbose_name="เบอร์ติดต่อ")),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("created_at", models.DateTimeField(verbose_name="วันที่สร้าง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
            ],
            options={
                "verbose_name": "Tutor",
                "verbose_name_plural": "Tutors",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="SchoolExpense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expense_date", models.DateField(verbose_name="วันที่จ่าย")),
                ("vendor", models.CharField(blank=True, max_length=255, verbose_name="Vendor / ผู้รับเงิน")),
                ("description", models.CharField(blank=True, max_length=255, verbose_name="รายละเอียด")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="จำนวนเงิน")),
                ("payment_method", models.CharField(choices=[("cash", "เงินสด"), ("transfer", "โอนเงิน"), ("qr", "QR / PromptPay"), ("card", "บัตร"), ("other", "อื่น ๆ")], default="transfer", max_length=20, verbose_name="วิธีจ่าย")),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(verbose_name="วันที่บันทึก")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expenses", to="core.expensecategory", verbose_name="ประเภทค่าใช้จ่าย")),
            ],
            options={
                "verbose_name": "School Expense",
                "verbose_name_plural": "School Expenses",
                "ordering": ("-expense_date", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="TutorPayrollEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("work_date", models.DateField(verbose_name="วันที่สอน")),
                ("teaching_hours", models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name="จำนวนชั่วโมงสอน")),
                ("hourly_rate", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="เรทต่อชั่วโมง")),
                ("teaching_fee", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="ค่าสอน")),
                ("travel_fee", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="ค่าเดินทาง")),
                ("idle_fee", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="ค่านั่งว่าง / ค่าอื่น ๆ")),
                ("total_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="ยอดรวม")),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(verbose_name="วันที่บันทึก")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("tutor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_entries", to="core.tutor", verbose_name="ติวเตอร์")),
            ],
            options={
                "verbose_name": "Tutor Payroll Entry",
                "verbose_name_plural": "Tutor Payroll Entries",
                "ordering": ("-work_date", "tutor__name"),
            },
        ),
        migrations.AddConstraint(
            model_name="tutorpayrollentry",
            constraint=models.UniqueConstraint(fields=("work_date", "tutor"), name="uniq_tutor_payroll_per_day"),
        ),
        migrations.RunPython(seed_finance_defaults, migrations.RunPython.noop),
    ]
