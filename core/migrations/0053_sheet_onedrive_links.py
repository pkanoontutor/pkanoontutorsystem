# -*- coding: utf-8 -*-
"""Fill in / correct SheetInventory.onedrive_url for every catalogued sheet.

Links point at the sheet's OneDrive *subfolder* (not a specific file inside
it), per how the sheet drive is organised: each subfolder holds the sheet's
เนื้อหา/ปก/เฉลย files together. The subfolder names below were read directly
from the live OneDrive listing (not guessed), and the resulting URLs were
spot-checked by navigating to a few of the trickier ones (parentheses,
mixed Thai/English) to confirm they resolve to the right folder.

Existing links are overwritten only when they differ from the correct one,
so this is safe to re-run.
"""

import urllib.parse

from django.db import migrations, models


_BASE_ID_PREFIX = (
    "/personal/31c861ffa0ce9918/Documents/Desktop/"
    "#พี่ขนุนติวเตอร์ - ชีทและเฉลย/"
    "#พี่ขนุนติวเตอร์ - ชีทและเฉลย 2569/"
)
_REDEEM = (
    "aHR0cHM6Ly8xZHJ2Lm1zL2YvYy8zMWM4NjFmZmEwY2U5OTE4L0lnQldXLUZWbGVnMFE0bzZaVDNJRzIyWkFY"
    "RThRVnNKVFYxWmNJMk9yNnp4Yks0P2U9aXAzZUFO"
)

# (grade folder name on OneDrive, [(sheet code, exact subfolder name), ...])
_GRADES = [
    ("ป.4 - 2569", [
        ("E-P4-01", "E-P4-01 อังกฤษ ป.4 พื้นฐานเล่ม 1"),
        ("M-P4-01", "M-P4-01 คณิต ป.4 เทอม 1 เล่ม A"),
        ("M-P4-02", "M-P4-02 คณิต ป.4 เทอม 1 เล่ม B"),
        ("SC-P4-01", "SC-P4-01 สังคม ป.4 ตะลุยโจทย์รวมบท"),
        ("S-P4-01", "S-P4-01 วิทย์ ป.4 พื้นฐาน + โจทย์ TEDET"),
        ("TH-P4-01", "TH-P4-01 ไทย การอ่าน ป.4 เล่ม 1"),
    ]),
    ("ป.5 - 2569", [
        ("E-P5-01", "E-P5-01 อังกฤษ ป.5 พื้นฐานเล่ม 1"),
        ("M-P5-01", "M-P5-01 คณิต ป.5 รวมบท เทอม 1-2"),
        ("ONP501", "ONP501 - คอร์สติวออนไลน์ ป.5 เล่ม 1"),
        ("SC-P5-01", "SC-P5-01 สังคม ป.5 ตะลุยโจทย์รวมบท"),
        ("S-P5-01", "S-P5-01 วิทย์ ป.5 พื้นฐานเล่ม 1"),
        ("TH-P5-01", "TH-P5-01 ไทย การอ่าน ป.5 เล่ม 1"),
    ]),
    ("ป.6 - 2569", [
        ("E-P6-01", "E-P6-01 อังกฤษ ป.6 พื้นฐานเล่ม 1"),
        ("E-P6-02", "E-P6-02 อังกฤษ ป.6 เล่ม 2 ตะลุยโจทย์ Lv.1"),
        ("EX-P6-01", "EX-P6-01 อังกฤษเสริม โจทย์ยาก ม.ต้น ป.6 เล่ม 1"),
        ("M-P6-01", "M-P6-01 คณิต ป.6 พื้นฐานเล่ม 1 (จาก ค-ป6-03)"),
        ("M-P6-02", "M-P6-02 คณิต ป.6 พื้นฐานเล่ม 2 (จาก ค-ป6-03)"),
        ("MX-P6-01", "MX-P6-01 คณิต ป.6 สมการขั้นเทพ"),
        ("MX-P6-02", "MX-P6-02 คณิตตะลุยโจทย์ ป.6 เล่ม 1"),
        ("SC-P6-01", "SC-P6-01 สังคม ป.6 เล่ม 1"),
        ("S-P6-01", "S-P6-01 วิทย์ ป.6 พื้นฐานเล่ม 1"),
        ("TH-P6-01", "TH-P6-01 ไทย ป.6 พื้นฐานเล่ม 1"),
    ]),
    ("ม.1 - 2569", [
        ("E-M1-01", "E-M1-01 อังกฤษ ม.1 เทอม 1"),
        ("E-M1-02", "E-M1-02 อังกฤษ ม.1 เทอม 2"),
        ("M-M1-01", "M-M1-01 คณิต ม.1 พื้นฐานเล่ม 1"),
        ("M-M1-02", "M-M1-02 คณิต ม.1 พื้นฐานเล่ม 2"),
        ("MX-M1-01", "MX-M1-01 คณิตเสริม ม.1 เทอม 1"),
        ("MX-M1-02", "MX-M1-02 คณิตเสริม ม.1 เทอม 2"),
        ("S-M1-01A", "S-M1-01A วิทย์ ม.1 เทอม 1 เล่ม A"),
        ("S-M1-01B", "S-M1-01B วิทย์ ม.1 เทอม 1 เล่ม B"),
    ]),
    ("ม.2 - 2569", [
        ("E-M2-01", "E-M2-01 อังกฤษ ม.2 รวม 2 เทอม"),
        ("M-M2-01", "M-M2-01 คณิต ม.2 เทอม 1"),
        ("M-M2-02", "M-M2-02 คณิตหลัก ม.2 เทอม 2"),
        ("MX-M2-01", "MX-M2-01 คณิตเสริม ม.2 รวม 2 เทอม"),
        ("S-M2-01", "S-M2-01 วิทย์ ม.2 เทอม 1 เล่ม A"),
        ("S-M2-02", "S-M2-02 วิทย์ ม.2 เทอม 1 เล่ม B"),
        ("S-M2-03", "S-M2-03 วิทย์ ม.2 เทอม 2 เล่ม C"),
        ("S-M2-04", "S-M2-04 วิทย์ ม.2 เทอม 2 เล่ม D"),
    ]),
    ("ม.3 - 2569", [
        ("E-M3-01", "E-M3-01 อังกฤษ ม.3 รวม 2 เทอม"),
        ("M-M3-01", "M-M3-01 คณิต ม.3 เทอม 1"),
        ("MX-M3-01", "MX-M3-01 คณิตเสริม ม.3 รวม 2 เทอม"),
        ("S-M3-01", "S-M3-01 วิทย์ ม.3 เทอม 1 เล่ม A"),
        ("S-M3-02", "S-M3-02 วิทย์ ม.3 เทอม 1 เล่ม B"),
    ]),
    ("ม.4 - 2569", [
        ("BIO-M4-01", "BIO-M4-01 ชีวะ ม.4 เล่ม 1"),
        ("CHEM-M4-01", "CHEM-M4-01 ตะลุยโจทย์เคมี ม.4 เทอม 1"),
        ("CHEM-M4-02", "CHEM-M4-02 ตะลุยโจทย์เคมี ม.4 เทอม 2"),
        ("E-M4-01", "E-M4-01 TGAT อังกฤษ ม.4 เล่ม 1"),
        ("M-M4-01", "M-M4-01 คณิตหลัก ม.4 เทอม 1-2"),
        ("MX-M4-01", "MX-M4-01 คณิตเสริม ม.4 เทอม 1 เล่ม 1"),
        ("MX-M4-02", "MX-M4-02 คณิตเสริม ม.4 เทอม 1 เล่ม 2"),
        ("PHY-M4-01", "PHY-M4-01 ตะลุยโจทย์ฟิสิกส์ ม.4 เทอม 1"),
        ("PHY-M4-02", "PHY-M4-02 ตะลุยโจทย์ฟิสิกส์ ม.4 เทอม 2"),
        ("SC-M4-01", "SC-M4-01 วิทย์กายภาพ ม.4"),
    ]),
    ("ม.5 - 2569", [
        ("E-M5-01", "E-M5-01 อังกฤษ ม.5 เล่ม 1"),
        ("M-M5-01A", "M-M5-01A คณิต ม.5 เทอม 1 ชุด A"),
        ("M-M5-01B", "M-M5-01B คณิต ม.5 เทอม 1 ชุด B"),
        ("TPAT-PHY-03", "TPAT-PHY-03 ฟิสิกส์ เล่ม 3"),
        ("TPAT-PHY-04", "TPAT-PHY-04 ฟิสิกส์ เล่ม 4"),
    ]),
]


def _build_url(grade_folder: str, subfolder: str) -> str:
    path = _BASE_ID_PREFIX + grade_folder + "/" + subfolder
    encoded_id = urllib.parse.quote(path, safe="")
    return (
        "https://onedrive.live.com/?id=" + encoded_id
        + "&listurl=%2Fpersonal%2F31c861ffa0ce9918%2FDocuments"
        + "&ithint=folder&migratedtospo=true"
        + "&redeem=" + _REDEEM + "&ga=1"
    )


def apply_links(apps, schema_editor):
    Sheet = apps.get_model("core", "Sheet")
    SheetInventory = apps.get_model("core", "SheetInventory")

    for grade_folder, sheets in _GRADES:
        for code, subfolder in sheets:
            sheet = Sheet.objects.filter(code=code).first()
            if sheet is None:
                continue
            url = _build_url(grade_folder, subfolder)
            inv, _ = SheetInventory.objects.get_or_create(sheet=sheet, defaults={"quantity": 0})
            if inv.onedrive_url != url:
                inv.onedrive_url = url
                inv.save(update_fields=["onedrive_url", "updated_at"])


def noop(apps, schema_editor):
    """Links are reference data -- rolling back leaves them in place."""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0052_sheet_cover_image_and_countdown_weekday"),
    ]

    operations = [
        # These OneDrive folder URLs embed the full nested folder path (in
        # Thai) inside the `id` query param, so they run well past the old
        # 1000-char cap -- the longest generated link is ~1100 chars, and
        # future sheets with longer names could go further still.
        migrations.AlterField(
            model_name="sheetinventory",
            name="onedrive_url",
            field=models.URLField(
                blank=True,
                help_text="ลิงก์ไฟล์ชีทสำหรับส่งร้านปรินท์",
                max_length=2000,
                verbose_name="ลิงก์ไฟล์ OneDrive",
            ),
        ),
        # SheetPrintOrder copies the sheet's link at order-creation time (see
        # admin_tool_create_print_order / create_print_order_inline), so it
        # needs the same headroom or that copy fails the same way.
        migrations.AlterField(
            model_name="sheetprintorder",
            name="onedrive_url",
            field=models.URLField(blank=True, max_length=2000, verbose_name="ลิงก์ไฟล์ OneDrive"),
        ),
        migrations.RunPython(apply_links, noop),
    ]
