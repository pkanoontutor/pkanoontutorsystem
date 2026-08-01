from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0044_cost_analysis_module"),
    ]

    operations = [
        migrations.AddField(
            model_name="coursepayment",
            name="receipt_kind",
            field=models.CharField(
                choices=[("course", "ค่าคอร์สเรียน"), ("other", "รายการอื่น (ไม่ผูกกับคอร์ส)")],
                default="course",
                max_length=20,
                verbose_name="ประเภทใบเสร็จ",
            ),
        ),
        migrations.AddField(
            model_name="coursepayment",
            name="item_description",
            field=models.CharField(
                blank=True,
                help_text="เช่น ค่าชีทสำหรับทดลองเรียน",
                max_length=200,
                verbose_name="รายการ (สำหรับใบเสร็จที่ไม่ผูกกับคอร์ส)",
            ),
        ),
        migrations.AlterField(
            model_name="coursepayment",
            name="tutoring_class",
            field=models.ForeignKey(
                blank=True,
                help_text="เว้นว่างได้สำหรับใบเสร็จประเภทรายการอื่นที่ไม่ผูกกับคอร์ส/Enrollment",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="course_payments",
                to="core.tutoringclass",
            ),
        ),
    ]
