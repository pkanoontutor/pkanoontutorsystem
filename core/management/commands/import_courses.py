from django.core.management.base import BaseCommand
from core.models import TutoringClass
import openpyxl
from pathlib import Path

class Command(BaseCommand):
    help = "Import courses from Excel"

    def handle(self, *args, **options):
        file_path = Path("data/courses.xlsx")

        if not file_path.exists():
            self.stderr.write("❌ File data/courses.xlsx not found")
            return

        wb = openpyxl.load_workbook(file_path)
        ws = wb.active

        imported = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            name, course_price, total_seats, hours_per_session, is_active = row

            if not name:
                continue

            TutoringClass.objects.update_or_create(
                name=name,
                defaults={
                    "course_price": course_price,
                    "total_seats": total_seats,
                    "hours_per_session": hours_per_session,
                    "is_active": bool(is_active),
                }
            )
            imported += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Imported {imported} courses successfully"
        ))
