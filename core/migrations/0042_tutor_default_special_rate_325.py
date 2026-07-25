from django.db import migrations, models


# Tutors that should default to the 325 THB/hr rate when teaching onsite >= 4 hrs.
SPECIAL_RATE_TUTOR_KEYWORDS = ["อีม", "ต้นข้าว", "บีม"]


def set_default_special_rates(apps, schema_editor):
    Tutor = apps.get_model("core", "Tutor")
    for keyword in SPECIAL_RATE_TUTOR_KEYWORDS:
        Tutor.objects.filter(name__icontains=keyword).update(default_special_rate_325=True)


def unset_default_special_rates(apps, schema_editor):
    Tutor = apps.get_model("core", "Tutor")
    Tutor.objects.update(default_special_rate_325=False)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_admintoolcard_star_quiz"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutor",
            name="default_special_rate_325",
            field=models.BooleanField(
                default=False,
                help_text="ถ้าติ๊ก ช่องเรทพิเศษ 325 จะถูกติ๊กให้อัตโนมัติเมื่อกรอกค่าสอนของติวเตอร์คนนี้",
                verbose_name="ค่าเริ่มต้นเรทพิเศษ 325 บาท/ชม.",
            ),
        ),
        migrations.RunPython(set_default_special_rates, unset_default_special_rates),
    ]
