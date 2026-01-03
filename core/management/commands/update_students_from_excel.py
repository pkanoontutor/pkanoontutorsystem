import openpyxl
from django.core.management.base import BaseCommand
from core.models import Student


class Command(BaseCommand):
    help = "Update students from Excel using student_code as key (NO CREATE)"

    def handle(self, *args, **options):
        path = "data/students_update.xlsx"
        wb = openpyxl.load_workbook(path)
        ws = wb.active

        updated = 0
        skipped = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            # รองรับไฟล์ที่มีแค่ 4 คอลัมน์
            student_code = str(row[0]).strip() if row[0] else ""
            nickname = row[1] if len(row) > 1 else None
            full_name = row[2] if len(row) > 2 else None
            grade_level = row[3] if len(row) > 3 else None

            if not student_code:
                skipped += 1
                continue

            try:
                student = Student.objects.get(student_code=student_code)
            except Student.DoesNotExist:
                self.stderr.write(f"❌ ไม่พบ student_code {student_code}")
                skipped += 1
                continue

            changed = False

            if nickname not in (None, ""):
                student.nickname = nickname
                changed = True

            if full_name not in (None, ""):
                student.full_name = full_name
                changed = True

            if grade_level not in (None, ""):
                student.grade_level = grade_level
                changed = True

            if changed:
                student.save()
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Update สำเร็จ {updated} คน | ⏭ ข้าม {skipped} แถว"
            )
        )
