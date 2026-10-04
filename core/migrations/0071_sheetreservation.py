import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0070_admintoolcard_session_adjustments"),
    ]

    operations = [
        migrations.CreateModel(
            name="SheetReservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1, verbose_name="จำนวน")),
                ("status", models.CharField(choices=[("reserved", "รอแจก"), ("handed_out", "แจกแล้ว"), ("released", "คืนคลังแล้ว")], default="reserved", max_length=20, verbose_name="สถานะ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("admission_inquiry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sheet_reservations", to="core.admissioninquiry", verbose_name="รายการสมัคร/ทดลองเรียน")),
                ("sheet", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reservations", to="core.sheet", verbose_name="ชีท")),
                ("tutoring_class", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sheet_reservations", to="core.tutoringclass", verbose_name="Class")),
                ("movement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="core.sheetinventorymovement", verbose_name="Movement ที่ตัด stock")),
                ("allocation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="core.sheetallocation", verbose_name="Sheet Allocation")),
            ],
            options={"verbose_name": "Sheet Reservation", "verbose_name_plural": "Sheet Reservations", "ordering": ("-created_at",)},
        ),
    ]
