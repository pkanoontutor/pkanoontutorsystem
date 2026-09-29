import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


# Income a tutoring school takes that never passes through a course receipt.
INCOME_CATEGORIES = [
    "ค่าชีท / หนังสือ (ขายแยก)",
    "ค่าเรียนชดเชย / เรียนเพิ่มรายครั้ง",
    "ค่าสมัครสอบ / สอบวัดระดับ",
    "ค่าคอร์สออนไลน์",
    "ค่ากิจกรรม / ค่ายเรียน",
    "ค่าอุปกรณ์ / ของใช้นักเรียน",
    "เงินมัดจำ / จองที่นั่ง",
    "ดอกเบี้ย / เงินคืน",
    "รายรับอื่น ๆ",
]

# Costs the original seed list did not cover. Staff wages in particular were
# missing entirely -- only tutor payroll existed -- so admin salaries had
# nowhere to go but "ค่าใช้จ่ายอื่น ๆ".
NEW_EXPENSE_CATEGORIES = [
    "เงินเดือนพนักงาน / แอดมิน",
    "ประกันสังคม / สวัสดิการพนักงาน",
    "ค่าทำบัญชี / ภาษี / ค่าธรรมเนียมราชการ",
    "ค่าของรางวัลนักเรียน",
    "ค่าคอมมิชชั่น / ค่าแนะนำเพื่อน",
    "ค่าตกแต่ง / ปรับปรุงสถานที่",
    "ค่าอาหาร / เลี้ยงรับรอง",
    "ค่าประกันภัย",
    "ค่าเช่าอุปกรณ์ / ครุภัณฑ์",
]


def seed(apps, schema_editor):
    IncomeCategory = apps.get_model("core", "IncomeCategory")
    for i, name in enumerate(INCOME_CATEGORIES, start=1):
        IncomeCategory.objects.get_or_create(
            name=name, defaults={"is_active": True, "sort_order": i},
        )

    ExpenseCategory = apps.get_model("core", "ExpenseCategory")
    base = (
        ExpenseCategory.objects.order_by("-sort_order")
        .values_list("sort_order", flat=True).first()
    ) or 0
    for i, name in enumerate(NEW_EXPENSE_CATEGORIES, start=1):
        ExpenseCategory.objects.get_or_create(
            name=name,
            defaults={"is_tutor_payroll": False, "is_active": True, "sort_order": base + i},
        )


def unseed(apps, schema_editor):
    # Only remove rows nothing points at, so a category that has been used
    # since is never silently deleted along with its history.
    IncomeCategory = apps.get_model("core", "IncomeCategory")
    IncomeCategory.objects.filter(name__in=INCOME_CATEGORIES, incomes__isnull=True).delete()
    ExpenseCategory = apps.get_model("core", "ExpenseCategory")
    ExpenseCategory.objects.filter(name__in=NEW_EXPENSE_CATEGORIES, expenses__isnull=True).delete()


class Migration(migrations.Migration):
    """Other-income recording + the flat 350/hr tutor rate.

    Hand-written: the local venv runs Django 6.0 against a 4.2.16 pin, so
    autodetect output would carry unrelated pre-existing drift.
    """

    dependencies = [
        ("core", "0067_attendance_half_deduction"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutorpayrollentry",
            name="special_rate_350",
            field=models.BooleanField(
                default=False,
                help_text="ห้องที่จ่าย 350 บาท/ชม. คงที่ (ตั้งต้นติ๊กให้ห้อง ป.5)",
                verbose_name="เรทห้องพิเศษ 350/ชม.",
            ),
        ),
        migrations.CreateModel(
            name="IncomeCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="ประเภทรายรับ")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="ลำดับ")),
            ],
            options={
                "verbose_name": "Income Category",
                "verbose_name_plural": "Income Categories",
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.CreateModel(
            name="OtherIncome",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("income_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="วันที่รับเงิน")),
                ("payer", models.CharField(blank=True, max_length=255, verbose_name="ผู้จ่าย / ลูกค้า")),
                ("description", models.CharField(blank=True, max_length=255, verbose_name="รายละเอียด")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="จำนวนเงิน")),
                ("payment_method", models.CharField(choices=[("cash", "เงินสด"), ("transfer", "โอนเงิน"), ("promptpay", "พร้อมเพย์ / QR"), ("other", "อื่น ๆ")], default="transfer", max_length=20, verbose_name="ช่องทางรับเงิน")),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่บันทึก")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incomes", to="core.incomecategory", verbose_name="ประเภทรายรับ")),
            ],
            options={
                "verbose_name": "Other Income",
                "verbose_name_plural": "Other Incomes",
                "ordering": ("-income_date", "-created_at"),
            },
        ),
        migrations.AddIndex(
            model_name="otherincome",
            index=models.Index(fields=["income_date"], name="core_otheri_income__8630e6_idx"),
        ),
        migrations.AlterField(
            model_name="admissioninquiry",
            name="preferred_time_slot",
            field=models.CharField(
                choices=[
                    ("sat_morning", "เสาร์เช้า (08.30-12.30)"),
                    ("sat_afternoon", "เสาร์บ่าย (13.30-17.30)"),
                    ("sun_morning", "อาทิตย์เช้า (08.30-12.30)"),
                    ("sun_afternoon", "อาทิตย์บ่าย (13.30-17.30)"),
                    ("weekday_holiday", "รอบปิดเทอมวันธรรมดา (จันทร์-ศุกร์)"),
                ],
                max_length=30,
                verbose_name="รอบเวลาเรียน",
            ),
        ),
        migrations.RunPython(seed, unseed),
    ]
