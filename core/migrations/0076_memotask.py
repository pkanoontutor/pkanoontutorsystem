import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

_URL = "/memos/"


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if AdminToolCard.objects.filter(url=_URL).exists():
        return
    max_order = (
        AdminToolCard.objects.filter(section="operation")
        .order_by("-order").values_list("order", flat=True).first()
    ) or 0
    AdminToolCard.objects.create(
        section="operation", icon="📝", name="Memo / Checklist",
        desc="จดงานที่ต้องทำ กำหนดวัน และผู้รับผิดชอบ (ตัวเอง / แอดมิน / ติวเตอร์) เชื่อมกับนักเรียนในภาพรวมเรียลไทม์ได้",
        url=_URL, color="c-sand", order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    apps.get_model("core", "AdminToolCard").objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0075_admintoolcard_tutor_schedule"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MemoTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.CharField(max_length=500, verbose_name="รายการ")),
                ("owner_name", models.CharField(blank=True, max_length=120, verbose_name="ผู้รับผิดชอบ")),
                ("due_date", models.DateField(blank=True, null=True, verbose_name="กำหนดเสร็จ")),
                ("is_done", models.BooleanField(default=False, verbose_name="เสร็จแล้ว")),
                ("done_at", models.DateTimeField(blank=True, null=True, verbose_name="เสร็จเมื่อ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="สร้างเมื่อ")),
                ("admission_inquiry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="memo_tasks", to="core.admissioninquiry", verbose_name="เชื่อมกับนักเรียนที่จะมาเรียน")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Memo Task", "verbose_name_plural": "Memo Tasks", "ordering": ("is_done", "due_date", "-created_at")},
        ),
        migrations.RunPython(add_card, remove_card),
    ]
