from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_teaching_update_no_teaching"),
    ]

    operations = [
        migrations.AddField(
            model_name="admissioninquiry",
            name="is_completed",
            field=models.BooleanField(default=False, verbose_name="ดำเนินการเสร็จแล้ว"),
        ),
        migrations.AddField(
            model_name="admissioninquiry",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="วันที่ดำเนินการเสร็จ"),
        ),
    ]
