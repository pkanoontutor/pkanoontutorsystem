import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

_URL = "/snack-shop/"


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if AdminToolCard.objects.filter(url=_URL).exists():
        return
    max_order = (
        AdminToolCard.objects.filter(section="private")
        .order_by("-order").values_list("order", flat=True).first()
    ) or 0
    AdminToolCard.objects.create(
        section="private", icon="🍬", name="รายรับรายจ่ายร้านขนม",
        desc="บันทึกรับเงินสด · ซื้อสินค้า · นำเงินไปแลกเหรียญ ของร้านขนม แยกจากบัญชีโรงเรียน",
        url=_URL, color="c-rose", order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    apps.get_model("core", "AdminToolCard").objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0076_memotask"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SnackShopEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entry_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="วันที่")),
                ("kind", models.CharField(choices=[("cash_in", "รับเงินสด"), ("purchase", "ซื้อสินค้า"), ("coin_exchange", "นำเงินไปแลกเหรียญ")], max_length=20, verbose_name="ประเภท")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="จำนวนเงิน")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="รายละเอียด")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="บันทึกเมื่อ")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Snack Shop Entry", "verbose_name_plural": "Snack Shop Entries", "ordering": ("-entry_date", "-created_at")},
        ),
        migrations.RunPython(add_card, remove_card),
    ]
