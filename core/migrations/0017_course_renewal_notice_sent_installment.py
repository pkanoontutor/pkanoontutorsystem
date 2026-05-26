# Generated manually for course renewal notice sent status and installment notices

from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0016_course_renewal_notice_module"),
    ]

    operations = [
        migrations.AddField(
            model_name="courserenewalnotice",
            name="notice_type",
            field=models.CharField(
                choices=[
                    ("renewal", "ใบแจ้งต่อคอร์ส"),
                    ("installment", "ใบแจ้งชำระงวดถัดไป"),
                ],
                default="renewal",
                max_length=20,
                verbose_name="ประเภทใบแจ้ง",
            ),
        ),
        migrations.AddField(
            model_name="courserenewalnotice",
            name="source_payment",
            field=models.ForeignKey(
                blank=True,
                help_text="ใช้กับใบแจ้งชำระงวดถัดไป เพื่ออ้างอิงใบเสร็จงวดแรกหรือรายการที่เกี่ยวข้อง",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="renewal_notices",
                to="core.coursepayment",
                verbose_name="ใบเสร็จอ้างอิง / งวดแรก",
            ),
        ),
        migrations.AddField(
            model_name="courserenewalnotice",
            name="installment_full_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="ยอดเต็มของคอร์ส ใช้กับใบแจ้งชำระงวดถัดไป",
                max_digits=10,
                verbose_name="แบ่งชำระ - ยอดเต็ม",
            ),
        ),
        migrations.AddField(
            model_name="courserenewalnotice",
            name="installment_paid_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="ยอดที่ชำระแล้ว ใช้กับใบแจ้งชำระงวดถัดไป",
                max_digits=10,
                verbose_name="แบ่งชำระ - ชำระแล้ว",
            ),
        ),
        migrations.AddField(
            model_name="courserenewalnotice",
            name="installment_remaining_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                help_text="ยอดคงเหลือ ระบบคำนวณจากยอดเต็ม - ชำระแล้ว แต่ยังสามารถแก้ยอดเต็ม/ชำระแล้วก่อนบันทึกได้",
                max_digits=10,
                verbose_name="แบ่งชำระ - ยอดคงเหลือ",
            ),
        ),
        migrations.AddField(
            model_name="courserenewalnotice",
            name="is_sent_to_parent",
            field=models.BooleanField(default=False, verbose_name="ส่งแจ้งผู้ปกครองแล้ว"),
        ),
        migrations.AddField(
            model_name="courserenewalnotice",
            name="sent_to_parent_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="วันที่ส่งแจ้งผู้ปกครอง"),
        ),
        migrations.AddField(
            model_name="courserenewalnotice",
            name="sent_to_parent_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sent_course_renewal_notices",
                to=settings.AUTH_USER_MODEL,
                verbose_name="ผู้กดส่งแจ้ง",
            ),
        ),
    ]
