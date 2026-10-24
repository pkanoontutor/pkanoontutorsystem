import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0082_official_docs"),
    ]

    operations = [
        migrations.CreateModel(
            name="MonthlyFixedExpense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=255, verbose_name="รายการ")),
                ("vendor", models.CharField(blank=True, max_length=255, verbose_name="ผู้รับเงิน")),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="จำนวนเงิน (ร่างของเดือนถัดไป)")),
                ("payment_method", models.CharField(default="transfer", max_length=20, verbose_name="ช่องทาง")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fixed_templates", to="core.expensecategory", verbose_name="ประเภทค่าใช้จ่าย")),
            ],
            options={"ordering": ("order", "id")},
        ),
        migrations.AddField(
            model_name="schoolexpense", name="fixed_template",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="expenses", to="core.monthlyfixedexpense"),
        ),
        migrations.AddField(
            model_name="schoolexpense", name="fixed_month",
            field=models.DateField(blank=True, null=True, verbose_name="รายจ่ายประจำของเดือน"),
        ),
    ]
