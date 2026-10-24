from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0083_monthly_fixed_expense"),
    ]

    operations = [
        migrations.AddField(model_name="tutor", name="bank_name", field=models.CharField(blank=True, max_length=100, verbose_name="ธนาคาร")),
        migrations.AddField(model_name="tutor", name="bank_account_no", field=models.CharField(blank=True, max_length=40, verbose_name="เลขที่บัญชี")),
        migrations.AddField(model_name="tutor", name="bank_account_name", field=models.CharField(blank=True, max_length=150, verbose_name="ชื่อบัญชี")),
    ]
