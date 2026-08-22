# Generated manually for P'Kanoon Tutor
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

_GRADE_CHOICES = [
    ("p4", "ป.4"), ("p5", "ป.5"), ("p6", "ป.6"), ("m1", "ม.1"),
    ("m2", "ม.2"), ("m3", "ม.3"), ("m4", "ม.4"), ("m5", "ม.5"),
]


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0055_admintoolcard_remaining_attendance"),
    ]

    operations = [
        migrations.CreateModel(
            name="Book",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True, verbose_name="รหัสหนังสือ")),
                ("title", models.CharField(max_length=255, verbose_name="ชื่อหนังสือ")),
                ("grade_level", models.CharField(blank=True, choices=_GRADE_CHOICES, default="", max_length=20, verbose_name="ระดับชั้น")),
                ("file_url", models.URLField(blank=True, max_length=2000, verbose_name="ลิงก์ไฟล์หนังสือ")),
                ("answer_location", models.CharField(choices=[("included", "รวมเฉลยในเล่ม"), ("separate", "มีเฉลยแยกเล่ม")], default="included", max_length=20, verbose_name="เฉลย")),
                ("answer_url", models.URLField(blank=True, help_text="ใช้เมื่อเลือก 'มีเฉลยแยกเล่ม'", max_length=2000, verbose_name="ลิงก์ไฟล์เฉลย")),
                ("cover_image", models.ImageField(blank=True, help_text="อัปโหลด JPG หรือ PNG ใช้เป็นรูปประจำหนังสือเล่มนี้", null=True, upload_to="book_covers/", verbose_name="รูปปก")),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="books", to="core.subject", verbose_name="วิชา")),
            ],
            options={
                "verbose_name": "Book",
                "verbose_name_plural": "Books",
                "ordering": ("grade_level", "subject__name", "code"),
            },
        ),
        migrations.AddField(
            model_name="sheet",
            name="source_book",
            field=models.ForeignKey(
                blank=True,
                help_text="ใช้อ้างอิงย้อนหลังว่าชีทนี้ทำมาจากหนังสือเล่มไหน",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sheets",
                to="core.book",
                verbose_name="สร้างจากหนังสือเล่ม",
            ),
        ),
        migrations.CreateModel(
            name="SheetDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("cover", "ปก"), ("content", "เนื้อหา"), ("answer", "เฉลย")], max_length=20, verbose_name="ประเภทไฟล์")),
                ("title", models.CharField(blank=True, help_text="เว้นว่างได้ ระบบจะใช้ชื่อไฟล์เดิม", max_length=255, verbose_name="ชื่อไฟล์ที่แสดง")),
                ("pdf", models.FileField(upload_to="sheet_documents/", verbose_name="ไฟล์ PDF")),
                ("thumbnail", models.ImageField(blank=True, help_text="สร้างอัตโนมัติจากหน้าแรกของ PDF ตอนอัปโหลด", null=True, upload_to="sheet_doc_thumbs/", verbose_name="รูปย่อหน้าแรก")),
                ("page_count", models.PositiveIntegerField(default=0, verbose_name="จำนวนหน้า")),
                ("source_url", models.URLField(blank=True, max_length=2000, verbose_name="ลิงก์อ้างอิง")),
                ("display_order", models.PositiveIntegerField(default=1, verbose_name="ลำดับ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่อัปโหลด")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("sheet", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="core.sheet", verbose_name="ชีท")),
                ("source_book", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sheet_documents", to="core.book", verbose_name="มาจากหนังสือเล่ม")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sheet_documents", to=settings.AUTH_USER_MODEL, verbose_name="ผู้อัปโหลด")),
            ],
            options={
                "verbose_name": "Sheet Document",
                "verbose_name_plural": "Sheet Documents",
                "ordering": ("sheet__code", "kind", "display_order", "id"),
            },
        ),
    ]
