from django.core.management.base import BaseCommand
from core.models import TutoringClass, Subject, ClassSubject
import openpyxl
from pathlib import Path

class Command(BaseCommand):
    help = "Import class-subject relationships from Excel"

    def handle(self, *args, **options):
        file_path = Path("data/class_subjects.xlsx")

        if not file_path.exists():
            self.stderr.write("❌ File data/class_subjects.xlsx not found")
            return

        wb = openpyxl.load_workbook(file_path)
        ws = wb.active

        imported = 0
        skipped = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            class_name, subject_name = row

            if not class_name or not subject_name:
                skipped += 1
                continue

            try:
                tutoring_class = TutoringClass.objects.get(name=class_name.strip())
                subject = Subject.objects.get(name=subject_name.strip())
            except (TutoringClass.DoesNotExist, Subject.DoesNotExist):
                skipped += 1
                continue

            ClassSubject.objects.get_or_create(
                tutoring_class=tutoring_class,
                subject=subject
            )
            imported += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Imported {imported} class-subject links ({skipped} skipped)"
        ))
