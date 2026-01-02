import openpyxl
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Student, TutoringClass, Enrollment


class Command(BaseCommand):
    help = "Import enrollments from Excel"

    def handle(self, *args, **options):
        path = "data/enrollments.xlsx"
        wb = openpyxl.load_workbook(path)
        ws = wb.active

        count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            (
                student_code,
                class_name,
                enrollment_type,
                sessions_total,
                payment_type,
                course_price,
                discount_amount,
                remark,
            ) = row

            try:
                student = Student.objects.get(student_code=str(student_code))
            except Student.DoesNotExist:
                self.stderr.write(f"❌ ไม่พบ student_code {student_code}")
                continue

            try:
                tutoring_class = TutoringClass.objects.get(name=class_name)
            except TutoringClass.DoesNotExist:
                self.stderr.write(f"❌ ไม่พบ class {class_name}")
                continue

            Enrollment.objects.create(
                student=student,
                tutoring_class=tutoring_class,
                enrollment_type=enrollment_type,
                sessions_total=int(sessions_total),
                payment_type=payment_type,
                course_price=course_price,
                discount_amount=discount_amount or 0,
                remark=remark or "",
                created_at=timezone.now(),
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Import enrollments สำเร็จ {count} รายการ"))
