"""Sheet cover images + per-weekday visibility for exam countdowns.

Hand-written for the same reason as 0050/0051: pre-existing drift between
models.py and the migration history makes ``makemigrations`` emit destructive
operations, so only the additive fields this feature needs are included.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0051_sheetinventory_storage_location"),
    ]

    operations = [
        migrations.AddField(
            model_name="sheet",
            name="cover_image",
            field=models.ImageField(
                blank=True,
                help_text="วางรูป (Ctrl+V) หรืออัปโหลดได้จากหน้า Sheet Inventory",
                null=True,
                upload_to="sheet_covers/",
                verbose_name="รูปหน้าปก",
            ),
        ),
        migrations.AddField(
            model_name="scheduleexamcountdown",
            name="show_on_saturday",
            field=models.BooleanField(default=True, verbose_name="แสดงในตารางวันเสาร์"),
        ),
        migrations.AddField(
            model_name="scheduleexamcountdown",
            name="show_on_sunday",
            field=models.BooleanField(default=True, verbose_name="แสดงในตารางวันอาทิตย์"),
        ),
    ]
