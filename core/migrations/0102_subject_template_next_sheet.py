from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0101_homework_star_multi"),
    ]

    operations = [
        migrations.AddField(
            model_name="teachingclasssubjecttemplate",
            name="next_sheet",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="next_for_subject_templates", to="core.sheet",
                verbose_name="ชีทเล่มถัดไป",
                help_text="เลือกจากภาพรวมเรียลไทม์เมื่อติวเตอร์แจ้งใกล้จบชีท จะขึ้นให้ติวเตอร์อัตโนมัติในการอัปเดตครั้งถัดไป",
            ),
        ),
    ]
