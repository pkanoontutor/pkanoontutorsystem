import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0098_print_supply_other_items"),
    ]

    operations = [
        migrations.CreateModel(
            name="RefundReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("refund_no", models.CharField(blank=True, max_length=20, unique=True, verbose_name="เลขที่ใบคืนเงิน")),
                ("refund_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="วันที่คืนเงิน")),
                ("recipient_type", models.CharField(choices=[("student", "นักเรียนในระบบ"), ("admission", "ผู้สมัคร (Student Admission)"), ("external", "บุคคลภายนอก")], max_length=20, verbose_name="ผู้รับเงินคืน")),
                ("recipient_name", models.CharField(max_length=255, verbose_name="ชื่อผู้รับเงินคืน")),
                ("recipient_phone", models.CharField(blank=True, max_length=50, verbose_name="เบอร์ติดต่อ")),
                ("items", models.JSONField(default=list, verbose_name="รายการคืนเงิน")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="ยอดคืนเงินรวม")),
                ("payment_method", models.CharField(choices=[("cash", "เงินสด"), ("transfer", "โอนเงิน"), ("qr", "QR / PromptPay"), ("card", "บัตร"), ("other", "อื่น ๆ")], default="transfer", max_length=20, verbose_name="วิธีคืนเงิน")),
                ("reason", models.TextField(blank=True, verbose_name="เหตุผล")),
                ("is_void", models.BooleanField(default=False, verbose_name="ยกเลิกแล้ว")),
                ("created_by", models.CharField(blank=True, max_length=150, verbose_name="ผู้ออกใบ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่บันทึก")),
                ("admission", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="refunds", to="core.admissioninquiry")),
                ("expense", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="refund_receipt", to="core.schoolexpense")),
                ("student", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="refunds", to="core.student")),
            ],
            options={"ordering": ("-refund_date", "-id")},
        ),
    ]
