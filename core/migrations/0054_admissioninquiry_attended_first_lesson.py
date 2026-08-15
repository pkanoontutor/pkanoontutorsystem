"""Track "arrived, awaiting receipt" separately from "ยกเลิก/เสร็จแล้ว" so the
admin tool's real-time overview can recolor a card without hiding it.

Hand-written for the same reason as 0050-0053: pre-existing drift between
models.py and the migration history makes ``makemigrations`` emit
destructive operations, so only the additive field this feature needs is
included.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0053_sheet_onedrive_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="admissioninquiry",
            name="attended_first_lesson",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "ติ๊กจากปุ่ม “มาแล้ว” ในภาพรวมเรียลไทม์ของ Admin Tool "
                    "-- การ์ดยังอยู่ต่อจนกว่าจะสร้างใบเสร็จ"
                ),
                verbose_name="มาเรียนแล้ว (รอสร้างใบเสร็จ)",
            ),
        ),
    ]
