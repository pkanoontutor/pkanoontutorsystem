from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0088_pretest_application"),
    ]

    operations = [
        migrations.AddField(
            model_name="pretestapplication",
            name="application_no",
            field=models.CharField(blank=True, max_length=30, verbose_name="เลขที่ใบสมัคร"),
        ),
        migrations.AddField(
            model_name="pretestapplication",
            name="application_pdf",
            field=models.BinaryField(blank=True, editable=False, null=True, verbose_name="ไฟล์ใบสมัคร"),
        ),
    ]
