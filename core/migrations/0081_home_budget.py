import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0080_online_schedule_one_hour"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeBudgetProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="ตกแต่งบ้านใหม่", max_length=120, verbose_name="ชื่อโปรเจกต์")),
                ("total_budget", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="งบประมาณทั้งหมด")),
                ("floor_plan", models.ImageField(blank=True, null=True, upload_to="home_budget/plans/", verbose_name="แปลนบ้าน")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name="HomeBudgetZone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, verbose_name="ชื่อโซน")),
                ("color", models.CharField(default="#6366f1", max_length=20, verbose_name="สี")),
                ("budget", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="งบของโซน (ไม่บังคับ)")),
                ("plan_x", models.FloatField(blank=True, null=True)),
                ("plan_y", models.FloatField(blank=True, null=True)),
                ("plan_w", models.FloatField(blank=True, null=True)),
                ("plan_h", models.FloatField(blank=True, null=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="zones", to="core.homebudgetproject")),
            ],
            options={"ordering": ("order", "id")},
        ),
        migrations.CreateModel(
            name="HomeBudgetItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("item", "ของที่จะซื้อ"), ("labor", "ค่าจ้าง / ค่าแรง")], default="item", max_length=10, verbose_name="ประเภท")),
                ("name", models.CharField(max_length=200, verbose_name="รายการ")),
                ("planned_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="งบที่ตั้งไว้")),
                ("vendor", models.CharField(blank=True, max_length=150, verbose_name="ร้าน / ผู้รับจ้าง")),
                ("note", models.CharField(blank=True, max_length=300, verbose_name="หมายเหตุ")),
                ("is_done", models.BooleanField(default=False, verbose_name="ซื้อ/จ้างครบแล้ว")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="core.homebudgetproject")),
                ("zone", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="items", to="core.homebudgetzone")),
            ],
            options={"ordering": ("is_done", "-created_at")},
        ),
        migrations.CreateModel(
            name="HomeBudgetExpense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("spent_on", models.DateField(default=django.utils.timezone.localdate, verbose_name="วันที่จ่าย")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="จำนวนเงินที่จ่ายจริง")),
                ("note", models.CharField(blank=True, max_length=300, verbose_name="หมายเหตุ")),
                ("receipt", models.FileField(blank=True, null=True, upload_to="home_budget/receipts/", verbose_name="ใบเสร็จ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expenses", to="core.homebudgetitem")),
            ],
            options={"ordering": ("-spent_on", "-id")},
        ),
    ]
