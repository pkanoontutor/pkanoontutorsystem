from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0104_enrollment_not_renewed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="courserenewalnotice", name="per_session_count",
            field=models.DecimalField(decimal_places=1, default=0, max_digits=6, verbose_name="รายครั้ง - จำนวนครั้ง"),
        ),
        migrations.AddField(
            model_name="courserenewalnotice", name="per_session_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="รายครั้ง - ราคาต่อครั้ง"),
        ),
        migrations.AddField(
            model_name="courserenewalnotice", name="per_session_only",
            field=models.BooleanField(default=False, verbose_name="แสดงเฉพาะรายครั้ง (ซ่อนแพ็กเกจ)"),
        ),
    ]
