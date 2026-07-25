from django.db import migrations, models


NEW_SHEET_CARD_NAME = "ระบบคลังชีทและส่งปรินท์ชีท"
NEW_SHEET_CARD_DESC = (
    "สร้างชีท จัดการ stock สแกน QR ตัด/นับชีท สั่งปรินท์และตรวจรับชีทจากร้านปรินท์ ครบในหน้าเดียว"
)


def apply_card_changes(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")

    # "+" shortcut on the receipt card -> straight to the create-receipt page.
    AdminToolCard.objects.filter(url="/course-payments/").update(
        quick_add_url="/course-payments/new/"
    )

    # Sheet print orders is now merged into Sheet Inventory: retire the separate
    # card and rebrand the inventory card to cover both jobs.
    AdminToolCard.objects.filter(url="/sheet-print-orders/").delete()
    AdminToolCard.objects.filter(url="/sheet-inventory/").update(
        name=NEW_SHEET_CARD_NAME,
        desc=NEW_SHEET_CARD_DESC,
    )

    # Point the export card at the new full multi-sheet export.
    AdminToolCard.objects.filter(url="/export/excel/").update(
        name="Export ข้อมูลทั้งระบบ",
        desc=(
            "Export ทุกหมวดเป็น Excel แยก sheet (นักเรียน คอร์ส ใบเสร็จ รายจ่าย ค่าสอน "
            "คลังชีท ผลเทส) และส่งเข้าอีเมลอัตโนมัติทุกวันศุกร์/อาทิตย์ 23.59 น."
        ),
        url="/export/excel/full/",
    )


def revert_card_changes(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url="/sheet-inventory/").update(
        name="Sheet Inventory",
        desc="สร้างชีท จัดการ stock สแกน QR ตัด/นับชีท และดูชีทที่ต้องใช้ตามรายการสมัคร/ทดลองเรียน",
    )
    # The deleted print-order card is intentionally not recreated: reversing the
    # merge is a manual decision, not something to guess at here.


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0042_tutor_default_special_rate_325"),
    ]

    operations = [
        migrations.AddField(
            model_name="admintoolcard",
            name="quick_add_url",
            field=models.CharField(
                blank=True,
                help_text="ถ้าใส่ จะมีปุ่ม + ที่มุมขวาบนของ card เพื่อลัดไปหน้าสร้างรายการใหม่",
                max_length=300,
                verbose_name="ลิงก์ปุ่ม + (ลัดไปหน้าสร้างใหม่)",
            ),
        ),
        migrations.RunPython(apply_card_changes, revert_card_changes),
    ]
