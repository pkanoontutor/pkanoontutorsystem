# Generated manually for CourseRenewalNotice installment detail fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_course_renewal_notice_sent_installment"),
    ]

    operations = [
        migrations.AddField(
            model_name="courserenewalnotice",
            name="installment_no",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(2, "งวดที่ 2"), (3, "งวดที่ 3"), (4, "งวดที่ 4")],
                help_text="ใช้กับใบแจ้งชำระงวดที่ 2/3/4",
                null=True,
                verbose_name="งวดที่แจ้งชำระ",
            ),
        ),
        migrations.AddField(
            model_name="courserenewalnotice",
            name="installment_sessions",
            field=models.PositiveIntegerField(
                default=0,
                help_text="กรอกเองสำหรับใบแจ้งชำระงวดที่ 2/3/4",
                verbose_name="จำนวนครั้งที่ให้เรียนจากงวดนี้",
            ),
        ),
    ]
