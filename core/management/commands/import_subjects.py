from django.core.management.base import BaseCommand
from core.models import Subject
import openpyxl
from pathlib import Path

class Command(BaseCommand):
    help = "Import subjects from Excel"

    def handle(self, *args, **options):
        file_path = Path("data/subjects.xlsx")

        if not file_path.exists():
            self.stderr.write("❌ File data/subjects.xlsx not found")
            return

        wb = openpyxl.load_workbook(file_path)
        ws = wb.active

        imported = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            name, is_active = row

            if not name:
                continue

            Subject.objects.update_or_create(
                name=name.strip(),
                defaults={
                    "is_active": bool(is_active)
                }
            )
            imported += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Imported {imported} subjects successfully"
        ))
