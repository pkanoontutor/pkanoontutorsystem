from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0073_homeworkstar"),
    ]

    operations = [
        migrations.AddField(model_name="courserenewalnotice", name="installment_count",
                            field=models.PositiveSmallIntegerField(default=0, verbose_name="จำนวนงวดทั้งหมด")),
        migrations.AddField(model_name="courserenewalnotice", name="installment_due_amount",
                            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="ยอดที่ต้องชำระงวดนี้")),
        migrations.AddField(model_name="courserenewalnotice", name="installment_due_date",
                            field=models.DateField(blank=True, null=True, verbose_name="กำหนดชำระงวดนี้")),
        migrations.AddField(model_name="courserenewalnotice", name="next_installment_amount",
                            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="ยอดงวดถัดไป (คงเหลือหลังงวดนี้)")),
        migrations.AddField(model_name="courserenewalnotice", name="next_installment_due_date",
                            field=models.DateField(blank=True, null=True, verbose_name="กำหนดชำระงวดถัดไป")),
    ]
