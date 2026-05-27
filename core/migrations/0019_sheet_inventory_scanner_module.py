from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0018_course_renewal_installment_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="sheetinventory",
            name="minimum_stock",
            field=models.PositiveIntegerField(default=0, help_text="ใช้สำหรับเตือนชีทใกล้หมด", verbose_name="ขั้นต่ำที่ควรมี"),
        ),
        migrations.CreateModel(
            name="SheetInventoryMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("movement_type", models.CharField(choices=[("add", "เพิ่ม stock"), ("deduct", "ตัด stock"), ("set", "ตั้งยอดจริง"), ("count", "นับ stock")], max_length=20, verbose_name="ประเภท movement")),
                ("quantity", models.PositiveIntegerField(default=0, verbose_name="จำนวน")),
                ("balance_before", models.IntegerField(default=0, verbose_name="ยอดก่อนทำรายการ")),
                ("balance_after", models.IntegerField(default=0, verbose_name="ยอดหลังทำรายการ")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่บันทึก")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sheet_inventory_movements", to=settings.AUTH_USER_MODEL, verbose_name="ผู้บันทึก")),
                ("sheet", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movements", to="core.sheet", verbose_name="ชีท")),
            ],
            options={
                "verbose_name": "Sheet Inventory Movement",
                "verbose_name_plural": "Sheet Inventory Movements",
                "ordering": ("-created_at", "-id"),
            },
        ),
        migrations.CreateModel(
            name="SheetClassMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity_per_student", models.PositiveIntegerField(default=1, help_text="ใช้คำนวณว่ารายการสมัคร/ทดลองเรียนต้องใช้ชีทกี่ชุด", verbose_name="จำนวนชีทต่อเด็ก 1 คน")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("sheet", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_mappings", to="core.sheet", verbose_name="ชีท")),
                ("tutoring_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sheet_mappings", to="core.tutoringclass", verbose_name="Class")),
            ],
            options={
                "verbose_name": "Sheet Class Mapping",
                "verbose_name_plural": "Sheet Class Mappings",
                "ordering": ("tutoring_class__time_slot", "tutoring_class__name", "sheet__code"),
            },
        ),
        migrations.AddConstraint(
            model_name="sheetclassmapping",
            constraint=models.UniqueConstraint(fields=("tutoring_class", "sheet"), name="uniq_sheet_mapping_per_class"),
        ),
    ]
