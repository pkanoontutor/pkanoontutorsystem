"""Where each sheet physically sits in the stock room.

Hand-written for the same reason as 0050: ``makemigrations`` still wants to
drop columns and recreate models because of pre-existing drift between
models.py and the migration history, so only the one additive field this
feature needs is included.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0050_sheet_page_counts_and_default_sheet"),
    ]

    operations = [
        migrations.AddField(
            model_name="sheetinventory",
            name="storage_location",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "ตำแหน่งที่วางชีทจริงในห้องเก็บของ เช่น ชั้น 2 ฝั่งซ้าย / กล่อง A3 "
                    "— ให้คนนับชีทกรอกไว้หาง่าย"
                ),
                max_length=120,
                verbose_name="ตำแหน่งวางชีท",
            ),
        ),
    ]
