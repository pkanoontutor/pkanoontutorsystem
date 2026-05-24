from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0011_tutor_payroll_special_online'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoursePayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receipt_no', models.CharField(blank=True, help_text='ระบบสร้างอัตโนมัติรูปแบบ YYMM-001', max_length=20, unique=True, verbose_name='เลขที่ใบเสร็จ')),
                ('payment_date', models.DateField(default=django.utils.timezone.localdate, verbose_name='วันที่รับเงิน')),
                ('enrollment_action', models.CharField(choices=[('new', 'สร้าง Enrollment ใหม่'), ('add_existing', 'เพิ่มจำนวนครั้งเข้า Enrollment เดิม')], default='new', max_length=20, verbose_name='การจัดการ Enrollment')),
                ('enrollment_created', models.BooleanField(default=False, verbose_name='สร้าง Enrollment ใหม่จากใบเสร็จนี้')),
                ('enrollment_sessions_before', models.IntegerField(blank=True, null=True, verbose_name='จำนวนครั้งก่อนเพิ่ม')),
                ('session_package', models.CharField(default='10', max_length=30, verbose_name='แพ็กเกจจำนวนครั้ง')),
                ('sessions_granted', models.PositiveIntegerField(default=10, verbose_name='จำนวนครั้งที่ให้เรียน')),
                ('course_price', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='ราคาคอร์ส')),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='ส่วนลด')),
                ('net_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='ราคาสุทธิ')),
                ('amount_paid', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='ยอดรับชำระ')),
                ('payment_type', models.CharField(choices=[('full', 'ชำระเต็ม'), ('installment', 'แบ่งชำระ')], default='full', max_length=20, verbose_name='รูปแบบการชำระ')),
                ('payment_method', models.CharField(choices=[('cash', 'เงินสด'), ('bank_transfer', 'โอนธนาคาร'), ('promptpay', 'PromptPay'), ('credit_card', 'บัตรเครดิต')], default='bank_transfer', max_length=20, verbose_name='วิธีชำระเงิน')),
                ('status', models.CharField(choices=[('issued', 'ออกใบเสร็จแล้ว'), ('cancelled', 'ยกเลิก')], default='issued', max_length=20, verbose_name='สถานะใบเสร็จ')),
                ('note', models.TextField(blank=True, verbose_name='หมายเหตุ')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='วันที่บันทึก')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='อัปเดตล่าสุด')),
                ('cancelled_at', models.DateTimeField(blank=True, null=True, verbose_name='วันที่ยกเลิก')),
                ('cancel_reason', models.TextField(blank=True, verbose_name='เหตุผลการยกเลิก')),
                ('cancelled_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cancelled_course_payments', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_course_payments', to=settings.AUTH_USER_MODEL)),
                ('enrollment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='course_payments', to='core.enrollment')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='course_payments', to='core.student')),
                ('tutoring_class', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='course_payments', to='core.tutoringclass')),
            ],
            options={
                'verbose_name': 'Course Payment / Receipt',
                'verbose_name_plural': 'Course Payments / Receipts',
                'ordering': ('-payment_date', '-created_at'),
            },
        ),
    ]
