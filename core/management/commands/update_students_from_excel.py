import openpyxl
from django.core.management.base import BaseCommand
from core.models import Student, School


class Command(BaseCommand):
    help = "Update students from Excel using student_code (NO CREATE)"

    def handle(self, *args, **options):
        path = "data/students_update.xlsx"
        wb = openpyxl.load_workbook(path)
        ws = wb.active

        updated = 0
        skipped = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            (
                student_code,
                full_name,
                nickname,
                grade_level,
                academic_year,
                school_name,
            ) = row

            if not student_code:
                continue

            student_code = str(student_code).strip()

            try:
                student = Student.objects.get(student_code=student_code)
            except Student.DoesNotExist:
                self.stderr.write(f"❌ ไม่พบ student_code {student_code} → ข้าม")
                skipped += 1
                continue

            # ---------- Update เฉพาะ field ที่มีค่า ----------
            if full_name:
                student.full_name = str(full_name).strip()

            if nickname:
                student.nickname = str(nickname).strip()

            if grade_level:
                student.grade_level = str(grade_level).strip()

            if academic_year:
                student.academic_year = str(academic_year).strip()

            if school_name:
                school_name = str(school_name).strip()
                school, _ = School.objects.get_or_create(name=school_name)
                student.school = school

            student.save()
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Update สำเร็จ {updated} คน | ⏭ ข้าม {skipped} คน"
            )
        )
