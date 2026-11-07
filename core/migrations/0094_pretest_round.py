import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def to_rounds(apps, schema_editor):
    """Rounds and dates already typed per child become preset rounds."""
    App = apps.get_model("core", "PretestApplication")
    Round = apps.get_model("core", "PretestRound")
    found = {}
    for a in App.objects.exclude(filing_round=None, filing_date=None):
        key = (a.filing_round, a.filing_date)
        if key not in found:
            found[key] = Round.objects.create(
                name=f"รอบ {a.filing_round}" if a.filing_round else "ไม่ระบุรอบ",
                filing_date=a.filing_date or timezone.localdate(),
            )
        App.objects.filter(id=a.id).update(round=found[key])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0093_pretest_filing"),
    ]

    operations = [
        migrations.CreateModel(
            name="PretestRound",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, verbose_name="ชื่อรอบ")),
                ("filing_date", models.DateField(verbose_name="วันที่ยื่น")),
            ],
            options={"ordering": ("filing_date", "id")},
        ),
        migrations.AddField(
            model_name="pretestapplication",
            name="round",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="applications", to="core.pretestround", verbose_name="รอบที่ยื่น"),
        ),
        migrations.RunPython(to_rounds, migrations.RunPython.noop),
        migrations.RemoveField(model_name="pretestapplication", name="filing_round"),
        migrations.RemoveField(model_name="pretestapplication", name="filing_date"),
    ]
