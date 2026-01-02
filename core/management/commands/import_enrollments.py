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
            # Validate student
            # -----------------------
            try:
                student = Student.objects.get(student_code=str(student_code).strip())
            except Student.DoesNotExist:
                self.stderr.write(f"❌ Row {row_no}: ไม่พบ student_code {student_code}")
                continue

            # -----------------------
            # Validate class
            # -----------------------
            try:
                tutoring_class = TutoringClass.objects.get(name=str(class_name).strip())
            except TutoringClass.DoesNotExist:
                self.stderr.write(f"❌ Row {row_no}: ไม่พบ class {class_name}")
                continue

            # -----------------------
            # Normalize numeric fields
            # -----------------------
            try:
                sessions_total = int(sessions_total)
            except Exception:
                self.stderr.write(f"❌ Row {row_no}: sessions_total ไม่ถูกต้อง ({sessions_total})")
                continue

            try:
                course_price = float(course_price) if course_price not in (None, "") else 0
            except Exception:
                self.stderr.write(f"❌ Row {row_no}: course_price ไม่ถูกต้อง ({course_price})")
                continue

            try:
                discount_amount = float(discount_amount) if discount_amount not in (None, "") else 0
            except Exception:
                self.stderr.write(f"❌ Row {row_no}: discount_amount ไม่ถูกต้อง ({discount_amount})")
                continue

            enrollment_type = str(enrollment_type).strip() if enrollment_type else Enrollment.EnrollmentType.SPECIAL
            payment_type = str(payment_type).strip() if payment_type else Enrollment.PaymentType.FULL
            remark = str(remark).strip() if remark else ""

            # -----------------------
            # Create Enrollment (สำคัญ)
            # -----------------------
            Enrollment.objects.create(
                student=student,
                tutoring_class=tutoring_class,
                enrollment_type=enrollment_type,

                # ✅ ใช้ค่าจริงจาก Excel ห้ามแก้
                sessions_total=sessions_total,

                payment_type=payment_type,
                course_price=course_price,
                discount_amount=discount_amount,
                net_price=max(course_price - discount_amount, 0),

                # ✅ FIX fields ที่ DB บังคับ NOT NULL
                is_active=True,
                notified_near_complete=False,
                installments_count=1,

                remark=remark,
                created_at=timezone.now(),
            )

            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ Import enrollments สำเร็จ {count} รายการ")
        )
