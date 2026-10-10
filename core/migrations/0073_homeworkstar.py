import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

_URL = "/homework-stars/"


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if AdminToolCard.objects.filter(url=_URL).exists():
        return
    max_order = (
        AdminToolCard.objects.filter(section="operation")
        .order_by("-order").values_list("order", flat=True).first()
    ) or 0
    AdminToolCard.objects.create(
        section="operation",
        icon="⭐",
        name="สะสมดาวส่งการบ้าน",
        desc="เลือกเด็กที่ส่งการบ้าน (เสิร์ชชื่อ หรือเลือกจากคลาส) กดบันทึก 1 ครั้ง = 1 ดาว ต่อรอบเรียน",
        url=_URL,
        color="c-sand",
        order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    apps.get_model("core", "AdminToolCard").objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0072_book_publisher_pdf"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeworkStar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lesson_date", models.DateField(verbose_name="วันที่เรียน")),
                ("redeemed_at", models.DateTimeField(blank=True, null=True, verbose_name="ใช้เป็นส่วนลดแล้วเมื่อ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่บันทึก")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("enrollment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="homework_stars", to="core.enrollment", verbose_name="Enrollment")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="homework_stars", to="core.student", verbose_name="นักเรียน")),
                ("tutoring_class", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="homework_stars", to="core.tutoringclass", verbose_name="Class")),
            ],
            options={"verbose_name": "Homework Star", "verbose_name_plural": "Homework Stars", "ordering": ("-lesson_date", "-created_at")},
        ),
        migrations.AddConstraint(
            model_name="homeworkstar",
            constraint=models.UniqueConstraint(fields=("enrollment", "lesson_date"), name="uniq_homework_star_per_lesson"),
        ),
        migrations.RunPython(add_card, remove_card),
    ]
