from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


NEW_CARD = {
    "section": "private",
    "color": "c-clay",
    "icon": "📊",
    "name": "วิเคราะห์รายได้-ต้นทุน-กำไร",
    "desc": (
        "ดูกำไรรายห้อง ปรับสมมติฐานค่าสอน/รายได้ต่อคนได้เอง ปันส่วน fixed cost "
        "หาจุดคุ้มทุน และจำลอง what-if"
    ),
    "url": "/revenue-analysis/",
}


def add_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    if not AdminToolCard.objects.exists():
        # Table is empty: the view seeds defaults (incl. this card) on first open.
        return
    if AdminToolCard.objects.filter(url=NEW_CARD["url"]).exists():
        return
    # Slot it right after the finance card so related tools sit together.
    finance = AdminToolCard.objects.filter(url="/school-finance/").first()
    order = (finance.order + 1) if finance else (
        (AdminToolCard.objects.filter(section="private").aggregate(
            m=models.Max("order")).get("m") or 0) + 10
    )
    AdminToolCard.objects.create(order=order, **NEW_CARD)


def remove_card(apps, schema_editor):
    AdminToolCard = apps.get_model("core", "AdminToolCard")
    AdminToolCard.objects.filter(url=NEW_CARD["url"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0043_admintoolcard_quick_add_and_sheet_merge"),
    ]

    operations = [
        migrations.CreateModel(
            name="CostScenario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="ชื่อ Scenario")),
                ("period_month", models.DateField(help_text="ใช้แค่เดือน/ปี (วันที่จะถูกปรับเป็นวันที่ 1 อัตโนมัติ)", verbose_name="เดือนที่วิเคราะห์")),
                ("allocation_method", models.CharField(choices=[("students", "ตามจำนวนนักเรียน (แนะนำ)"), ("hours", "ตามชั่วโมงสอน"), ("revenue", "ตามสัดส่วนรายได้"), ("equal", "หารเท่ากันทุกห้อง")], default="students", max_length=20, verbose_name="วิธีปันส่วน Fixed Cost")),
                ("default_teaching_cost_per_hour", models.DecimalField(decimal_places=2, default=Decimal("300"), max_digits=10, verbose_name="ค่าสอนต่อชั่วโมง (ค่าเริ่มต้น)")),
                ("default_revenue_per_student_hour", models.DecimalField(decimal_places=2, default=Decimal("150"), max_digits=10, verbose_name="รายได้ต่อคนต่อชั่วโมง (ค่าเริ่มต้น)")),
                ("default_hours_per_session", models.DecimalField(decimal_places=2, default=Decimal("4"), max_digits=5, verbose_name="ชั่วโมงต่อครั้ง (ค่าเริ่มต้น)")),
                ("default_sessions_per_month", models.DecimalField(decimal_places=2, default=Decimal("4"), help_text="ปกติ 1 สัปดาห์เรียน 1 ครั้ง", max_digits=5, verbose_name="จำนวนครั้งต่อเดือน (ค่าเริ่มต้น)")),
                ("note", models.TextField(blank=True, verbose_name="บันทึก")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="สร้างเมื่อ")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
            ],
            options={
                "verbose_name": "Cost Scenario",
                "verbose_name_plural": "Cost Scenarios",
                "ordering": ("-period_month", "-updated_at"),
            },
        ),
        migrations.CreateModel(
            name="CostScenarioFixedCost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="รายการ")),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="จำนวนเงินต่อเดือน")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="หมายเหตุ")),
                ("order", models.IntegerField(default=0, verbose_name="ลำดับ")),
                ("scenario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fixed_costs", to="core.costscenario", verbose_name="Scenario")),
            ],
            options={
                "verbose_name": "Cost Scenario Fixed Cost",
                "verbose_name_plural": "Cost Scenario Fixed Costs",
                "ordering": ("order", "id"),
            },
        ),
        migrations.CreateModel(
            name="CostScenarioClass",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_included", models.BooleanField(default=True, verbose_name="รวมในการวิเคราะห์")),
                ("student_count", models.PositiveIntegerField(default=0, verbose_name="จำนวนนักเรียน")),
                ("sessions_per_month", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="จำนวนครั้งในเดือนนี้")),
                ("hours_per_session", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name="ชั่วโมงต่อครั้ง")),
                ("teaching_cost_per_hour", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="ค่าสอนต่อชั่วโมง")),
                ("revenue_per_student_hour", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="รายได้ต่อคนต่อชั่วโมง")),
                ("other_variable_cost", models.DecimalField(decimal_places=2, default=0, help_text="เช่น ค่าชีท ค่าขนม เฉพาะห้องนี้", max_digits=12, verbose_name="ต้นทุนผันแปรอื่นต่อเดือน")),
                ("scenario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_inputs", to="core.costscenario", verbose_name="Scenario")),
                ("tutoring_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cost_inputs", to="core.tutoringclass", verbose_name="Class")),
            ],
            options={
                "verbose_name": "Cost Scenario Class Input",
                "verbose_name_plural": "Cost Scenario Class Inputs",
                "ordering": ("tutoring_class__name",),
            },
        ),
        migrations.AddConstraint(
            model_name="costscenarioclass",
            constraint=models.UniqueConstraint(
                fields=("scenario", "tutoring_class"), name="uniq_cost_scenario_class"
            ),
        ),
        migrations.RunPython(add_card, remove_card),
    ]
