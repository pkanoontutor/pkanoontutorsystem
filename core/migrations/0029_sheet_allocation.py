# Generated manually for P'Kanoon Tutor
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_sheet_print_order_receive"),
    ]

    operations = [
        migrations.CreateModel(
            name="SheetAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1, verbose_name="จำนวนที่แจก")),
                ("allocation_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="วันที่แจก")),
                ("recipient_type", models.CharField(choices=[("student", "Student ในระบบ"), ("admission", "สมัครเรียน/ทดลองเรียน"), ("manual", "กรอกเอง"), ("unassigned", "ไม่ระบุชื่อ")], default="unassigned", max_length=20, verbose_name="ประเภทผู้รับ")),
                ("manual_nickname", models.CharField(blank=True, max_length=100, verbose_name="ชื่อเล่นที่กรอกเอง")),
                ("manual_grade_level", models.CharField(blank=True, max_length=50, verbose_name="ระดับชั้นที่กรอกเอง")),
                ("scan_code", models.CharField(blank=True, max_length=80, verbose_name="รหัสที่สแกน")),
                ("batch_key", models.CharField(blank=True, max_length=40, verbose_name="Batch")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่บันทึก")),
                ("admission_inquiry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sheet_allocations", to="core.admissioninquiry", verbose_name="รายการสมัคร/ทดลองเรียน")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sheet_allocations", to="auth.user", verbose_name="ผู้บันทึก")),
                ("movement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="allocations", to="core.sheetinventorymovement", verbose_name="Movement ที่ตัด stock")),
                ("sheet", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="allocations", to="core.sheet", verbose_name="ชีท")),
                ("student", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sheet_allocations", to="core.student", verbose_name="นักเรียนในระบบ")),
                ("tutoring_class", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sheet_allocations", to="core.tutoringclass", verbose_name="Class ที่เกี่ยวข้อง")),
            ],
            options={
                "verbose_name": "Sheet Allocation",
                "verbose_name_plural": "Sheet Allocations",
                "ordering": ("-allocation_date", "-created_at", "sheet__code"),
            },
        ),
        migrations.AddIndex(
            model_name="sheetallocation",
            index=models.Index(fields=["allocation_date", "recipient_type"], name="core_sheeta_allocat_3e1a58_idx"),
        ),
        migrations.AddIndex(
            model_name="sheetallocation",
            index=models.Index(fields=["sheet", "allocation_date"], name="core_sheeta_sheet_i_87b3e9_idx"),
        ),
        migrations.AddIndex(
            model_name="sheetallocation",
            index=models.Index(fields=["student", "allocation_date"], name="core_sheeta_student_2f874e_idx"),
        ),
        migrations.AddIndex(
            model_name="sheetallocation",
            index=models.Index(fields=["tutoring_class", "allocation_date"], name="core_sheeta_tutorin_3c75b6_idx"),
        ),
    ]
