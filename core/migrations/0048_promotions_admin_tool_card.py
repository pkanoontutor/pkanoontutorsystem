from django.db import migrations, models


NEW_CARD = {
    "section": "private",
    "color": "c-rose",
    "icon": "🎁",
    "name": "ระบบโปรโมชั่น",
    "desc": "ดูโปรโมชั่นทั้งหมด เริ่มจากเพื่อนชวนเพื่อน ใครชวนใครบ้าง กี่คน ได้เครดิตเท่าไร",
    "url": "/promotions/",
}


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if not AdminToolCard.objects.exists():
        # Table is empty: the view seeds defaults (incl. this card) on first open.
        return
    if AdminToolCard.objects.filter(url=NEW_CARD["url"]).exists():
        return
    renewal = AdminToolCard.objects.filter(url="/course-renewal-notices/").first()
    order = (renewal.order + 1) if renewal else (
        (AdminToolCard.objects.filter(section="private").aggregate(
            m=models.Max("order")).get("m") or 0) + 10
    )
    AdminToolCard.objects.create(order=order, **NEW_CARD)


def remove_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url=NEW_CARD["url"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0047_friend_referral_promotion"),
    ]

    operations = [
        migrations.RunPython(add_card, remove_card),
    ]
