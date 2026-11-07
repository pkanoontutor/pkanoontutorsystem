import django.db.models.deletion
from django.db import migrations, models

_URL = "/print-shop/supplies/"
_SEED = [
    ("cover_paper", "กระดาษปก", "แผ่น", 10),
    ("a4_paper", "กระดาษ A4", "แผ่น", 20),
    ("ink", "หมึก", "ชิ้น", 30),
    ("drum", "Drum หมึก", "ชิ้น", 40),
]


def seed(apps, schema_editor):
    PrintSupply = apps.get_model("core", "PrintSupply")
    for category, name, unit, order in _SEED:
        PrintSupply.objects.get_or_create(category=category, spine_color="", spine_size="",
                                          defaults={"name": name, "unit": unit, "order": order})
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if not AdminToolCard.objects.filter(url=_URL).exists():
        max_order = (
            AdminToolCard.objects.filter(section="private")
            .order_by("-order").values_list("order", flat=True).first()
        ) or 0
        AdminToolCard.objects.create(
            section="private", icon="📦", name="สินค้าคงคลังงานปรินท์",
            desc="กระดาษปก กระดาษ A4 สันสีต่างๆ หมึก Drum หักอัตโนมัติเมื่อสั่งปรินท์ พร้อมประวัติการแก้ไข",
            url=_URL, color="c-teal", order=max_order + 10,
        )


def unseed(apps, schema_editor):
    apps.get_model("core", "AdminToolCard").objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0090_pretest_is_external"),
    ]

    operations = [
        migrations.CreateModel(
            name="PrintSupply",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("cover_paper", "กระดาษปก"), ("a4_paper", "กระดาษ A4"), ("spine", "สันรูด"), ("ink", "หมึก"), ("drum", "Drum หมึก")], max_length=20, verbose_name="ประเภท")),
                ("name", models.CharField(max_length=100, verbose_name="ชื่อ")),
                ("spine_color", models.CharField(blank=True, max_length=20, verbose_name="สีสัน")),
                ("spine_size", models.CharField(blank=True, max_length=30, verbose_name="ขนาดสัน")),
                ("unit", models.CharField(default="ชิ้น", max_length=20, verbose_name="หน่วย")),
                ("quantity", models.IntegerField(default=0, verbose_name="คงเหลือ")),
                ("low_threshold", models.PositiveIntegerField(default=0, verbose_name="เตือนเมื่อเหลือไม่เกิน")),
                ("is_active", models.BooleanField(default=True)),
                ("order", models.PositiveIntegerField(default=50)),
            ],
            options={
                "ordering": ("order", "spine_color", "spine_size"),
                "constraints": [models.UniqueConstraint(fields=("category", "spine_color", "spine_size"), name="uniq_print_supply")],
            },
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="print_sides",
            field=models.CharField(choices=[("single", "ด้านเดียว"), ("double", "หน้าหลัง")], default="single", max_length=10, verbose_name="การปรินท์"),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="content_pages",
            field=models.PositiveIntegerField(default=0, verbose_name="จำนวนหน้าเนื้อหาต่อเล่ม"),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="covers_used",
            field=models.PositiveIntegerField(default=0, verbose_name="กระดาษปกที่หัก"),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="a4_used",
            field=models.PositiveIntegerField(default=0, verbose_name="กระดาษ A4 ที่หัก"),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="spine_used",
            field=models.PositiveIntegerField(default=0, verbose_name="สันที่หัก"),
        ),
        migrations.AddField(
            model_name="sheetprintorder",
            name="spine_supply",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to="core.printsupply", verbose_name="ขนาดสันที่ร้านเลือก"),
        ),
        migrations.CreateModel(
            name="PrintSupplyLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delta", models.IntegerField(verbose_name="เปลี่ยนแปลง")),
                ("balance_after", models.IntegerField(verbose_name="คงเหลือหลังเปลี่ยน")),
                ("reason", models.CharField(choices=[("order", "สั่งปรินท์"), ("spine", "ร้านเลือกสัน"), ("spine_return", "คืนสัน (เปลี่ยนขนาด)"), ("adjust", "แก้ไขเอง")], max_length=20, verbose_name="สาเหตุ")),
                ("actor", models.CharField(blank=True, max_length=100, verbose_name="โดย")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="supply_logs", to="core.sheetprintorder")),
                ("supply", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs", to="core.printsupply")),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
        migrations.RunPython(seed, unseed),
    ]
