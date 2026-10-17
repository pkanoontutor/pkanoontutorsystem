import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0078_online_schedule"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SubAdminTool",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="ชื่อหน้า / ชื่อแอดมิน")),
                ("slug", models.SlugField(max_length=40, unique=True, verbose_name="ลิงก์")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="ข้อความต้อนรับ")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cards", models.ManyToManyField(blank=True, related_name="sub_admin_tools", to="core.admintoolcard", verbose_name="เมนูที่ให้ใช้")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sub_admin_tools", to=settings.AUTH_USER_MODEL, verbose_name="บัญชีผู้ใช้ของแอดมิน")),
            ],
            options={"verbose_name": "Sub Admin Tool", "verbose_name_plural": "Sub Admin Tools", "ordering": ("name",)},
        ),
    ]
