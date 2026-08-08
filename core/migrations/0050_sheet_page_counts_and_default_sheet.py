"""Sheet page counts + a per-class-subject default sheet link.

Written by hand rather than via ``makemigrations``: the autodetector currently
reports a large amount of pre-existing drift between models.py and the
migration history (it wants to drop columns and recreate models that
production already relies on), so this migration deliberately contains only
the additive operations this feature needs.

The page counts come from counting pages of the "เนื้อหา" PDF in each sheet
folder of the 2569 sheet drive.
"""

from django.db import migrations, models
import django.db.models.deletion


# (code, title, grade_level, subject_name, total_pages)
SHEET_PAGES = [
    ('E-P4-01', 'อังกฤษ ป.4 พื้นฐานเล่ม 1', 'p4', 'ภาษาอังกฤษ', 166),
    ('M-P4-01', 'คณิต ป.4 เทอม 1 เล่ม A', 'p4', 'คณิตศาสตร์', 186),
    ('M-P4-02', 'คณิต ป.4 เทอม 1 เล่ม B', 'p4', 'คณิตศาสตร์', 241),
    ('S-P4-01', 'วิทย์ ป.4 พื้นฐาน + โจทย์ TEDET', 'p4', 'วิทยาศาสตร์', 164),
    ('SC-P4-01', 'สังคม ป.4 ตะลุยโจทย์รวมบท', 'p4', 'สังคมศึกษา', 131),
    ('TH-P4-01', 'ไทย การอ่าน ป.4 เล่ม 1', 'p4', 'ภาษาไทย', 116),
    ('E-P5-01', 'อังกฤษ ป.5 พื้นฐานเล่ม 1', 'p5', 'ภาษาอังกฤษ', 160),
    ('M-P5-01', 'คณิต ป.5 รวมบท เทอม 1-2', 'p5', 'คณิตศาสตร์', 252),
    ('ONP501', 'คอร์สติวออนไลน์ ป.5 เล่ม 1', 'p5', 'อื่นๆ', 67),
    ('S-P5-01', 'วิทย์ ป.5 พื้นฐานเล่ม 1', 'p5', 'วิทยาศาสตร์', 161),
    ('SC-P5-01', 'สังคม ป.5 ตะลุยโจทย์รวมบท', 'p5', 'สังคมศึกษา', 183),
    ('TH-P5-01', 'ไทย การอ่าน ป.5 เล่ม 1', 'p5', 'ภาษาไทย', 122),
    ('E-P6-01', 'อังกฤษ ป.6 พื้นฐานเล่ม 1', 'p6', 'ภาษาอังกฤษ', 163),
    ('E-P6-02', 'อังกฤษ ป.6 เล่ม 2 ตะลุยโจทย์  Lv.1', 'p6', 'ภาษาอังกฤษ', 124),
    ('EX-P6-01', 'อังกฤษเสริม โจทย์ยาก ม.ต้น ป.6 เล่ม 1', 'p6', 'ภาษาอังกฤษ', 120),
    ('M-P6-01', 'คณิต ป.6 พื้นฐานเล่ม 1 (จาก ค-ป6-03)', 'p6', 'คณิตศาสตร์', 292),
    ('M-P6-02', 'คณิต ป.6 พื้นฐานเล่ม 2 (จาก ค-ป6-03)', 'p6', 'คณิตศาสตร์', 130),
    ('MX-P6-01', 'คณิต ป.6 สมการขั้นเทพ', 'p6', 'คณิตศาสตร์', 85),
    ('MX-P6-02', 'คณิตตะลุยโจทย์ ป.6 เล่ม 1', 'p6', 'คณิตศาสตร์', 145),
    ('S-P6-01', 'วิทย์ ป.6 พื้นฐานเล่ม 1', 'p6', 'วิทยาศาสตร์', 225),
    ('SC-P6-01', 'สังคม ป.6 เล่ม 1', 'p6', 'สังคมศึกษา', 137),
    ('TH-P6-01', 'ไทย ป.6 พื้นฐานเล่ม 1', 'p6', 'ภาษาไทย', 151),
    ('E-M1-01', 'อังกฤษ ม.1 เทอม 1', 'm1', 'ภาษาอังกฤษ', 140),
    ('E-M1-02', 'อังกฤษ ม.1 เทอม 2', 'm1', 'ภาษาอังกฤษ', 150),
    ('M-M1-01', 'คณิต ม.1 พื้นฐานเล่ม 1', 'm1', 'คณิตศาสตร์', 169),
    ('M-M1-02', 'คณิต ม.1 พื้นฐานเล่ม 2', 'm1', 'คณิตศาสตร์', 169),
    ('MX-M1-01', 'คณิตเสริม ม.1 เทอม 1', 'm1', 'คณิตศาสตร์', 110),
    ('MX-M1-02', 'คณิตเสริม ม.1 เทอม 2', 'm1', 'คณิตศาสตร์', 116),
    ('S-M1-01A', 'วิทย์ ม.1 เทอม 1 เล่ม A', 'm1', 'วิทยาศาสตร์', 110),
    ('S-M1-01B', 'วิทย์ ม.1 เทอม 1 เล่ม B', 'm1', 'วิทยาศาสตร์', 107),
    ('E-M2-01', 'อังกฤษ ม.2 รวม 2 เทอม', 'm2', 'ภาษาอังกฤษ', 153),
    ('M-M2-01', 'คณิต ม.2 เทอม 1', 'm2', 'คณิตศาสตร์', 169),
    ('M-M2-02', 'คณิตหลัก ม.2 เทอม 2', 'm2', 'คณิตศาสตร์', 161),
    ('MX-M2-01', 'คณิตเสริม ม.2 รวม 2 เทอม', 'm2', 'คณิตศาสตร์', 127),
    ('S-M2-01', 'วิทย์ ม.2 เทอม 1 เล่ม A', 'm2', 'วิทยาศาสตร์', 141),
    ('S-M2-02', 'วิทย์ ม.2 เทอม 1 เล่ม B', 'm2', 'วิทยาศาสตร์', 184),
    ('S-M2-03', 'วิทย์ ม.2 เทอม 2 เล่ม C', 'm2', 'วิทยาศาสตร์', 138),
    ('S-M2-04', 'วิทย์ ม.2 เทอม 2 เล่ม D', 'm2', 'วิทยาศาสตร์', 134),
    ('E-M3-01', 'อังกฤษ ม.3 รวม 2 เทอม', 'm3', 'ภาษาอังกฤษ', 157),
    ('M-M3-01', 'คณิต ม.3 เทอม 1', 'm3', 'คณิตศาสตร์', 153),
    ('MX-M3-01', 'คณิตเสริม ม.3 รวม 2 เทอม', 'm3', 'คณิตศาสตร์', 165),
    ('S-M3-01', 'วิทย์ ม.3 เทอม 1 เล่ม A', 'm3', 'วิทยาศาสตร์', 157),
    ('S-M3-02', 'วิทย์ ม.3 เทอม 1 เล่ม B', 'm3', 'วิทยาศาสตร์', 149),
    ('BIO-M4-01', 'ชีวะ ม.4 เล่ม 1', 'm4', 'ชีววิทยา', 165),
    ('CHEM-M4-01', 'ตะลุยโจทย์เคมี ม.4 เทอม 1', 'm4', 'เคมี', 157),
    ('CHEM-M4-02', 'ตะลุยโจทย์เคมี ม.4 เทอม 2', 'm4', 'เคมี', 183),
    ('E-M4-01', 'TGAT อังกฤษ ม.4 เล่ม 1', 'm4', 'ภาษาอังกฤษ', 198),
    ('M-M4-01', 'คณิตหลัก ม.4 เทอม 1-2', 'm4', 'คณิตศาสตร์', 164),
    ('MX-M4-01', 'คณิตเสริม ม.4 เทอม 1 เล่ม 1', 'm4', 'คณิตศาสตร์', 122),
    ('MX-M4-02', 'คณิตเสริม ม.4 เทอม 1 เล่ม 2', 'm4', 'คณิตศาสตร์', 122),
    ('PHY-M4-01', 'ตะลุยโจทย์ฟิสิกส์ ม.4 เทอม 1', 'm4', 'ฟิสิกส์', 129),
    ('PHY-M4-02', 'ตะลุยโจทย์ฟิสิกส์ ม.4 เทอม 2', 'm4', 'ฟิสิกส์', 167),
    ('SC-M4-01', 'วิทย์กายภาพ ม.4', 'm4', 'วิทยาศาสตร์กายภาพ', 223),
    ('E-M5-01', 'อังกฤษ ม.5 เล่ม 1', 'm5', 'ภาษาอังกฤษ', 144),
    ('M-M5-01A', 'คณิต ม.5 เทอม 1 ชุด A', 'm5', 'คณิตศาสตร์', 170),
    ('M-M5-01B', 'คณิต ม.5 เทอม 1 ชุด B', 'm5', 'คณิตศาสตร์', 135),
    ('TPAT-PHY-03', 'ฟิสิกส์ เล่ม 3', 'm5', 'ฟิสิกส์', 125),
    ('TPAT-PHY-04', 'ฟิสิกส์ เล่ม 4', 'm5', 'ฟิสิกส์', 153),
]


def apply_page_counts(apps, schema_editor):
    Sheet = apps.get_model("core", "Sheet")
    Subject = apps.get_model("core", "Subject")

    subject_cache = {}
    for code, title, grade_level, subject_name, total_pages in SHEET_PAGES:
        sheet = Sheet.objects.filter(code=code).first()
        if sheet is not None:
            # Existing sheets keep their admin-entered title/subject; only fill
            # in the page count and a missing grade level.
            changed = []
            if sheet.total_pages != total_pages:
                sheet.total_pages = total_pages
                changed.append("total_pages")
            if not sheet.grade_level and grade_level:
                sheet.grade_level = grade_level
                changed.append("grade_level")
            if changed:
                sheet.save(update_fields=changed)
            continue

        if subject_name not in subject_cache:
            subject_cache[subject_name], _ = Subject.objects.get_or_create(
                name=subject_name, defaults={"is_active": True}
            )
        Sheet.objects.create(
            code=code,
            title=title,
            subject=subject_cache[subject_name],
            grade_level=grade_level,
            total_pages=total_pages,
            total_questions=0,
            is_active=True,
        )


def noop(apps, schema_editor):
    """Page counts are reference data -- rolling back leaves them in place."""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0049_renewal_notice_quick_pick_dismiss"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sheet",
            name="grade_level",
            field=models.CharField(
                blank=True,
                choices=[
                    ("p4", "ป.4"),
                    ("p5", "ป.5"),
                    ("p6", "ป.6"),
                    ("m1", "ม.1"),
                    ("m2", "ม.2"),
                    ("m3", "ม.3"),
                    ("m4", "ม.4"),
                    ("m5", "ม.5"),
                ],
                default="",
                help_text="ใช้จัดกลุ่มชีทใน Sheet Inventory และช่วย filter ชีทให้ตรงกับ class",
                max_length=20,
                verbose_name="ระดับชั้น",
            ),
        ),
        migrations.AlterField(
            model_name="sheet",
            name="total_pages",
            field=models.PositiveIntegerField(
                default=0,
                help_text="จำนวนหน้าของไฟล์เนื้อหา ใช้คำนวณ % ความคืบหน้าการสอนในหน้าอัปเดตติวเตอร์",
                verbose_name="จำนวนหน้า",
            ),
        ),
        migrations.AddField(
            model_name="teachingclasssubjecttemplate",
            name="default_sheet",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "ปกติระบบจับคู่ชีทให้อัตโนมัติจากรหัสชีทที่ติวเตอร์กรอก "
                    "ตั้งค่านี้เมื่ออยากบังคับให้ใช้ชีทเล่มนี้คิด % แทนการจับคู่อัตโนมัติ"
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_for_subject_templates",
                to="core.sheet",
                verbose_name="ชีทในระบบ (ใช้คิด % ความคืบหน้า)",
            ),
        ),
        migrations.RunPython(apply_page_counts, noop),
    ]
