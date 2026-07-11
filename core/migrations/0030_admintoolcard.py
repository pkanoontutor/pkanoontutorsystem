# Generated manually for P'Kanoon Tutor
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_sheet_allocation"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminToolCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section", models.CharField(choices=[("private", "Private / Management"), ("operation", "Operation")], default="private", max_length=20, verbose_name="หมวด")),
                ("icon", models.CharField(default="🔗", max_length=16, verbose_name="ไอคอน")),
                ("name", models.CharField(max_length=200, verbose_name="ชื่อเมนู")),
                ("desc", models.TextField(blank=True, verbose_name="คำอธิบาย")),
                ("url", models.CharField(max_length=300, verbose_name="ลิงก์")),
                ("color", models.CharField(default="c-sky", max_length=20, verbose_name="สีไอคอน")),
                ("order", models.IntegerField(default=0, verbose_name="ลำดับ")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Admin Tool Card",
                "verbose_name_plural": "Admin Tool Cards",
                "ordering": ("section", "order", "id"),
            },
        ),
    ]
