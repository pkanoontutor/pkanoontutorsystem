from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0099_refund_receipt"),
    ]

    operations = [
        migrations.AlterField(
            model_name="courserenewalnotice",
            name="note_wording",
            field=models.TextField(default="ผู้ปกครองสามารถขอชะลอจ่าย เลื่อนจ่ายเป็นสิ้นเดือนได้โดยนักเรียนไม่ต้องเว้นวรรคการเรียนครับ ติดต่อแจ้งพี่ขนุนทาง Line ID : @pkanoontutor ครับ", verbose_name="ข้อความท้ายใบแจ้ง"),
        ),
    ]
