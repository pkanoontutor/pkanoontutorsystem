from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0071_sheetreservation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="book",
            name="grade_level",
            field=models.CharField(blank=True, choices=[("p4", "ป.4"), ("p5", "ป.5"), ("p6", "ป.6"), ("m1", "ม.1"), ("m2", "ม.2"), ("m3", "ม.3"), ("m4", "ม.4"), ("m5", "ม.5"), ("m6", "ม.6"), ("upper_primary", "ประถมปลาย"), ("lower_secondary", "มัธยมต้น"), ("upper_secondary", "มัธยมปลาย")], default="", max_length=20, verbose_name="ระดับชั้น"),
        ),
        migrations.AddField(
            model_name="book",
            name="publisher",
            field=models.CharField(blank=True, max_length=255, verbose_name="สำนักพิมพ์"),
        ),
        migrations.AddField(
            model_name="book",
            name="pdf_file",
            field=models.FileField(blank=True, null=True, upload_to="book_files/", verbose_name="ไฟล์หนังสือ (PDF)"),
        ),
        migrations.AddField(
            model_name="book",
            name="answer_pdf",
            field=models.FileField(blank=True, null=True, upload_to="book_files/", verbose_name="ไฟล์เฉลย (PDF)"),
        ),
        migrations.AddField(
            model_name="book",
            name="page_count",
            field=models.PositiveIntegerField(default=0, verbose_name="จำนวนหน้า"),
        ),
    ]
