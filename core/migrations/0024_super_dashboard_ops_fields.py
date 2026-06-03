from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_sheet_print_order_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="admissioninquiry",
            name="target_class",
            field=models.ForeignKey(
                blank=True,
                help_text="ใช้สำหรับประมาณที่นั่งว่างและติดตามเด็กสมัคร/ทดลองเรียน",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="admission_inquiries",
                to="core.tutoringclass",
                verbose_name="Class ที่คาดว่าจะเข้าเรียน",
            ),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="printed_quantity",
            field=models.PositiveIntegerField(default=0, verbose_name="จำนวนที่ร้านปรินท์เสร็จแล้ว"),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="print_done",
            field=models.BooleanField(default=False, verbose_name="ปรินท์แล้ว"),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="bound_done",
            field=models.BooleanField(default=False, verbose_name="เย็บแล้ว"),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="spine_unavailable",
            field=models.BooleanField(default=False, verbose_name="สันรูดหมด / รอสันรูด"),
        ),
    ]
