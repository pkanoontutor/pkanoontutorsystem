import django.db.models.deletion
from django.db import migrations, models

_URL = "/pretest-applications/"


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if AdminToolCard.objects.filter(url=_URL).exists():
        return
    max_order = (
        AdminToolCard.objects.filter(section="private")
        .order_by("-order").values_list("order", flat=True).first()
    ) or 0
    AdminToolCard.objects.create(
        section="private", icon="📝", name="ใบสมัครสอบ Pre-test",
        desc="รายชื่อเด็กที่ฝากยื่นใบสมัคร เช็กลิสต์ปรินท์ · เซ็น · รับเงิน · ยื่น · ส่งกลับ และหมายเลขผู้สอบ",
        url=_URL, color="c-lilac", order=max_order + 10,
    )


def remove_card(apps, schema_editor):
    apps.get_model("core", "AdminToolCard").objects.filter(url=_URL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0087_newstudentnotice_custom"),
    ]

    operations = [
        migrations.CreateModel(
            name="PretestApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nickname", models.CharField(blank=True, max_length=100, verbose_name="ชื่อเล่น")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="ชื่อจริง")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="นามสกุล")),
                ("national_id", models.CharField(max_length=13, unique=True, verbose_name="เลขบัตรประชาชน")),
                ("phone", models.CharField(blank=True, max_length=20, verbose_name="เบอร์มือถือ")),
                ("submitted_at", models.DateTimeField(blank=True, null=True, verbose_name="เวลาที่กรอกฟอร์ม")),
                ("is_printed", models.BooleanField(default=False, verbose_name="ปรินท์แล้ว")),
                ("is_signed", models.BooleanField(default=False, verbose_name="ส่งใบให้เด็กเซ็นแล้ว")),
                ("is_paid", models.BooleanField(default=False, verbose_name="รับเงินจากเด็กแล้ว")),
                ("is_filed", models.BooleanField(default=False, verbose_name="นำไปยื่นแล้ว")),
                ("is_returned", models.BooleanField(default=False, verbose_name="ส่งกลับให้เด็กแล้ว")),
                ("exam_number", models.CharField(blank=True, max_length=50, verbose_name="หมายเลขผู้สอบ")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("student", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pretest_applications", to="core.student", verbose_name="นักเรียนในระบบ")),
            ],
            options={"ordering": ("submitted_at", "id")},
        ),
        migrations.RunPython(add_card, remove_card),
    ]
