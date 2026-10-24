from django.db import migrations

_URL = "/extras/"


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if AdminToolCard.objects.filter(url=_URL).exists():
        return
    max_order = (
        AdminToolCard.objects.filter(section="private")
        .order_by("-order").values_list("order", flat=True).first()
    ) or 0
    AdminToolCard.objects.create(
        section="private", icon="🧩", name="ระบบส่วนเสริม",
        desc="เครื่องมือส่วนตัวนอกเหนือระบบกวดวิชา เช่น งบตกแต่งบ้าน",
        url=_URL, color="c-teal", order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    apps.get_model("core", "AdminToolCard").objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0084_tutor_bank"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
