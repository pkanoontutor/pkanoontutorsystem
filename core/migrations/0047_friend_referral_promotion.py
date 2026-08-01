import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0046_tutor_payroll_rate_travel_override"),
    ]

    operations = [
        migrations.CreateModel(
            name="FriendReferral",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("credit_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="มูลค่าเครดิตที่ผู้ชวนได้รับ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่ชวนสำเร็จ")),
                ("receipt", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="friend_referrals", to="core.coursepayment", verbose_name="ใบเสร็จของนักเรียนใหม่ที่บันทึกการชวนนี้")),
                ("referred_student", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="referred_by_entries", to="core.student", verbose_name="ผู้ถูกชวน (นักเรียนใหม่)")),
                ("referrer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="referrals_made", to="core.student", verbose_name="ผู้ชวน")),
            ],
            options={
                "verbose_name": "Friend Referral",
                "verbose_name_plural": "Friend Referrals",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddField(
            model_name="courserenewalnotice",
            name="referral_credit_used",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="หักออกจากราคาสุทธิของทุกแพ็กเกจ/ยอดคงเหลือในใบแจ้งนี้ ไม่เกินเครดิตคงเหลือของนักเรียนคนนี้",
                max_digits=10,
                verbose_name="ใช้เครดิตชวนเพื่อนเป็นส่วนลด",
            ),
        ),
    ]
