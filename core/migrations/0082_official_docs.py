from django.db import migrations, models

_URL = "/official-docs/"


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if AdminToolCard.objects.filter(url=_URL).exists():
        return
    max_order = (
        AdminToolCard.objects.filter(section="private")
        .order_by("-order").values_list("order", flat=True).first()
    ) or 0
    AdminToolCard.objects.create(
        section="private", icon="📄", name="ออกเอกสารทางการ",
        desc="ใบสลิปค่าจ้างรายสัปดาห์ และหนังสือรับรองการหักภาษี ณ ที่จ่าย (50 ทวิ) ของติวเตอร์ พร้อมข้อมูลผู้ถูกหักภาษี",
        url=_URL, color="c-stone", order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    apps.get_model("core", "AdminToolCard").objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0081_home_budget"),
    ]

    operations = [
        migrations.AddField(model_name="tutor", name="first_name", field=models.CharField(blank=True, max_length=120, verbose_name="ชื่อจริง")),
        migrations.AddField(model_name="tutor", name="last_name", field=models.CharField(blank=True, max_length=120, verbose_name="นามสกุล")),
        migrations.AddField(model_name="tutor", name="national_id", field=models.CharField(blank=True, max_length=20, verbose_name="เลขประจำตัวผู้เสียภาษี (13 หลัก)")),
        migrations.AddField(model_name="tutor", name="address", field=models.CharField(blank=True, max_length=400, verbose_name="ที่อยู่")),
        migrations.AddField(model_name="tutor", name="default_withhold_3", field=models.BooleanField(default=False, help_text="ถ้าติ๊ก ตอนส่งค่าติวเตอร์ช่อง 'หัก 3%' จะถูกติ๊กให้คนนี้อัตโนมัติ", verbose_name="ค่าเริ่มต้นหักภาษี ณ ที่จ่าย 3%")),
        migrations.AddField(model_name="tutorpayrollentry", name="withholding_3", field=models.BooleanField(default=False, verbose_name="หักภาษี ณ ที่จ่าย 3%")),
        migrations.AddField(model_name="tutorpayrollentry", name="withholding_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="ภาษีหัก ณ ที่จ่าย")),
        migrations.AddField(model_name="tutorpayrollentry", name="net_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="ยอดโอนสุทธิ")),
        migrations.RunSQL("UPDATE core_tutorpayrollentry SET net_amount = total_amount", migrations.RunSQL.noop),
        migrations.CreateModel(
            name="DocumentIssuer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="พี่ขนุนติวเตอร์", max_length=200, verbose_name="ชื่อผู้จ่ายเงิน / สถาบัน")),
                ("tax_id", models.CharField(blank=True, max_length=20, verbose_name="เลขประจำตัวผู้เสียภาษี")),
                ("address", models.CharField(blank=True, max_length=400, verbose_name="ที่อยู่")),
                ("signer_name", models.CharField(blank=True, max_length=150, verbose_name="ชื่อผู้ลงนาม")),
                ("signer_position", models.CharField(blank=True, default="ผู้จ่ายเงิน", max_length=100, verbose_name="ตำแหน่งผู้ลงนาม")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RunPython(add_card, remove_card),
    ]
