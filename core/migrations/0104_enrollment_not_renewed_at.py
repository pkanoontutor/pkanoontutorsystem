from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0103_admintoolcard_size"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollment",
            name="not_renewed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="กดไม่ต่อคอร์สเมื่อ",
                                       help_text="ตั้งจากปุ่ม 🚫 บน dashboard -- การ์ดจะแสดงเป็นสีเทาท้ายห้อง และกด ↩ ดึงกลับได้"),
        ),
    ]
