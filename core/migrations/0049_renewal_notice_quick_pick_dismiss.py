from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0048_promotions_admin_tool_card"),
    ]

    operations = [
        migrations.AddField(
            model_name="courserenewalnotice",
            name="hide_from_quick_receipt_pick",
            field=models.BooleanField(
                default=False,
                help_text="ติ๊กเมื่อกดกากบาทลบการ์ดนี้ออกจากรายการลัดในหน้าออกใบเสร็จ (ไม่ได้ลบใบแจ้งจริง)",
                verbose_name="ซ่อนจากการ์ดลัดในหน้าออกใบเสร็จ",
            ),
        ),
    ]
