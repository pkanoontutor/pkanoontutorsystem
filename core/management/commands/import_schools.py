from django.core.management.base import BaseCommand
from core.models import School
import openpyxl
from pathlib import Path

class Command(BaseCommand):
    help = "Import schools from Excel"

    def handle(self, *args, **options):
        file_path = Path("data/schools.xlsx")

        if not file_path.exists():
            self.stderr.write("❌ File data/schools.xlsx not found")
            return

        wb = openpyxl.load_workbook(file_path)
        ws = wb.active

        imported = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            (name,) = row
            if not name:
                continue

            School.objects.get_or_create(
                name=name.strip()
            )
            imported += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Imported {imported} schools successfully"
        ))
