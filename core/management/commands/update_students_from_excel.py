import openpyxl
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Student, School


class Command(BaseCommand):
    help = "Update students from Excel (SAFE MODE: update only, skip blank cells)"

    def set_if_has_value(self, obj, field, value):
        """
        ตั้งค่า field เฉพาะกรณีมีค่า (ไม่ None / ไม่ว่าง)
        """
        if value is not None and str(value).strip() != "":
            setattr(obj, field, str(value).strip())
            return True
        return False

    def handle(self, *args, **options):
        path = "data/update_students.xlsx"

        try:
            wb = openpyxl.load_workbook(path)
        except FileNotFoundError:
            self.stderr.write(f"❌ ไม่พบไฟล์ {path}")
            return

        ws = wb.active

        updated = 0
        skipped = 0

        self.stdout.write("🚀 เริ่มอัปเดตข้อมูลนักเรียน (SAFE MODE)")

        for row_no, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not row[0]:
                skipped += 1
                continue

            (
                student_code,
                nickname,
                full_name,
                grade_level,
                academic_year,
                school_name,
            ) = (list(row) + [None] * 6)[:6]

            try:
                student = Student.objects.get(student_code=str(student_code).strip())
            except Student.DoesNotExist:
                self.stderr.write(
                    f"❌ แถว {row_no}: ไม่พบ student_code {student_code}"
                )
                skipped += 1
                continue

            changed_fields = []

            with transaction.atomic():
                if self.set_if_has_value(student, "nickname", nickname):
                    changed_fields.append("nickname")

                if self.set_if_has_value(student, "full_name", full_name):
                    changed_fields.append("full_name")

                if self.set_if_has_value(student, "grade_level", grade_level):
                    changed_fields.append("grade_level")

                if self.set_if_has_value(student, "academic_year", academic_year):
                    changed_fields.append("academic_year")

                # School (lookup / create)
                if school_name and str(school_name).strip():
                    school_name = str(school_name).strip()
                    school, _ = School.objects.get_or_create(
                        name=school_name,
                        defaults={"is_active": True},
                    )
                    student.school = school
                    changed_fields.append("school")

                if changed_fields:
                    student.save(update_fields=changed_fields)
                    updated += 1
                    self.stdout.write(
                        f"✅ {student.student_code} อัปเดต: {', '.join(changed_fields)}"
                    )
                else:
                    skipped += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"🎉 เสร็จสิ้น | อัปเดต {updated} คน | ข้าม {skipped} แถว"
        ))
