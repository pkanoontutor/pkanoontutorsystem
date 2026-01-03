import openpyxl
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Student, TutoringClass, Enrollment


class Command(BaseCommand):
    help = "Import enrollments from Excel"

    def handle(self, *args, **options):
        print("🔥 USING NEW IMPORT FILE VERSION 🔥")

        path = "data/enrollments.xlsx"
        wb = openpyxl.load_workbook(path)
        ws = wb.active

        count = 0

        for row_no, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
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

            # -----------------------
            # Student
            # -----------------------
            try:
                student = Student.objects.get(student_code=str(student_code).strip())
            except Student.DoesNotExist:
                self.stderr.write(f"❌ Row {row_no}: ไม่พบ student_code {student_code}")
                continue

            # -----------------------
            # Class
            # -----------------------
            try:
                tutoring_class = TutoringClass.objects.get(name=str(class_name).strip())
            except TutoringClass.DoesNotExist:
                self.stderr.write(f"❌ Row {row_no}: ไม่พบ class {class_name}")
                continue

            # -----------------------
            # Numbers
            # -----------------------
            try:
                sessions_total = int(sessions_total)
            except Exception:
                self.stderr.write(f"❌ Row {row_no}: sessions_total ไม่ถูกต้อง")
                continue

            course_price = float(course_price or 0)
            discount_amount = float(discount_amount or 0)

            enrollment_type = str(enrollment_type).strip() if enrollment_type else Enrollment.EnrollmentType.SPECIAL
            payment_type = str(payment_type).strip() if payment_type else Enrollment.PaymentType.FULL
            remark = str(remark).strip() if remark else ""

            Enrollment.objects.create(
                student=student,
                tutoring_class=tutoring_class,
                enrollment_type=enrollment_type,

                # ✅ ใช้ค่าจริงจาก Excel
                sessions_total=sessions_total,

                payment_type=payment_type,
                installments_count=1,

                course_price=course_price,
                discount_amount=discount_amount,
                net_price=max(course_price - discount_amount, 0),

                # ❌ ไม่ส่ง field ที่ DB ไม่รู้จัก
                is_active=True,

                remark=remark,
                created_at=timezone.now(),
            )

            count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Import enrollments สำเร็จ {count} รายการ"))
