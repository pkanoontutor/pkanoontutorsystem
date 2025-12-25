from django.db import models, transaction
from django.utils import timezone


# -----------------------
# Student
# -----------------------
class Student(models.Model):
    class ContactChannel(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        LINE = "line", "Line"

    # ✅ ช่องทางที่รู้จัก
    class ReferralSource(models.TextChoices):
        REFERRAL = "referral", "คนแนะนำ"
        FACEBOOK = "facebook", "Facebook"
        GOOGLE = "google", "Google"
        FLYER = "flyer", "ใบปลิว"
        WALKIN = "walkin", "เดินผ่าน"

    # ✅ รหัสนักเรียนอัตโนมัติ: YY + 3 หลัก เช่น 25001
    student_code = models.CharField(
        "รหัสนักเรียน",
        max_length=5,
        unique=True,
        blank=True,
        help_text="ระบบสร้างอัตโนมัติรูปแบบ YY### เช่น 25001",
    )

    full_name = models.CharField("ชื่อจริงนามสกุล", max_length=255)
    nickname = models.CharField("ชื่อเล่น", max_length=100, blank=True)
    profile_image = models.ImageField("รูปประจำตัว", upload_to="student_profiles/", blank=True, null=True)

    grade_level = models.CharField("ระดับชั้น", max_length=50, blank=True)
    academic_year = models.CharField("ปีการศึกษา", max_length=20, blank=True)

    school_name = models.CharField("โรงเรียน", max_length=255, blank=True)

    parent_phone = models.CharField("เบอร์ผู้ปกครอง", max_length=50)

    contact_channel = models.CharField(
        "ช่องทางติดต่อ",
        max_length=20,
        choices=ContactChannel.choices,
        default=ContactChannel.LINE,
    )

    # ✅ วันที่สมัคร + ช่องทางที่รู้จัก
    enroll_date = models.DateField("วันที่สมัคร", default=timezone.localdate)
    referral_source = models.CharField(
        "ช่องทางที่รู้จัก",
        max_length=20,
        choices=ReferralSource.choices,
        default=ReferralSource.REFERRAL,
    )

    note = models.TextField("หมายเหตุ", blank=True)
    is_active = models.BooleanField("ใช้งานอยู่", default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        code = (self.student_code or "").strip()
        nick = (self.nickname or "").strip()
        full = (self.full_name or "").strip()
        grade = (self.grade_level or "").strip()

        parts = []
        if code:
            parts.append(code)
        if nick:
            parts.append(nick)
        if full:
            parts.append(full)
        if grade:
            parts.append(grade)

        return " | ".join(parts) if parts else "-"

    @staticmethod
    def _next_student_code_for_year(two_digit_year: str) -> str:
        """
        หา student_code ล่าสุดของปีนั้น แล้ว +1
        - ปี 2025 => "25"
        - คนแรก => 25001
        """
        last = (
            Student.objects.filter(student_code__startswith=two_digit_year)
            .order_by("-student_code")
            .values_list("student_code", flat=True)
            .first()
        )
        if not last:
            seq = 1
        else:
            seq = int(last[-3:]) + 1
        return f"{two_digit_year}{seq:03d}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding  # เพิ่มใหม่หรือแก้ไข
        if is_new:
            yy = str(timezone.localdate().year)[-2:]
            with transaction.atomic():
                self.student_code = Student._next_student_code_for_year(yy)
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)


# -----------------------
# Class (ห้อง/กลุ่ม)
# -----------------------
class TutoringClass(models.Model):
    name = models.CharField("ชื่อคลาส", max_length=100, unique=True)  # เช่น "ป.6 ห้อง A"

    # ✅ เพิ่ม: ราคาคอร์สเต็ม (ใช้ดึงไปใส่ใน Enrollment)
    course_price = models.DecimalField("ราคาคอร์ส (เต็ม)", max_digits=10, decimal_places=2, default=0)

    # ✅ (ข้อ 1) เพิ่ม: ที่นั่งรวม (ต้องกรอกตอนสร้าง Class)
    total_seats = models.PositiveIntegerField(
        "ที่นั่งรวม",
        default=0,
        help_text="จำนวนที่นั่งทั้งหมดของห้องนี้ (ใช้คำนวณ ระหว่างเรียน/ที่นั่งว่าง บน Dashboard)",
    )

    hours_per_session = models.DecimalField("ชั่วโมงต่อครั้ง", max_digits=4, decimal_places=2, default=3.00)
    is_active = models.BooleanField("เปิดใช้งาน", default=True)

    class Meta:
        verbose_name = "Class"
        verbose_name_plural = "Classes"

    def __str__(self) -> str:
        return self.name


# -----------------------
# Subject (วิชา)
# -----------------------
class Subject(models.Model):
    name = models.CharField("ชื่อวิชา", max_length=100, unique=True)
    is_active = models.BooleanField("เปิดใช้งาน", default=True)

    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


# -----------------------
# Sheet (ชีท) - Admin เพิ่มได้
# -----------------------
class Sheet(models.Model):
    code = models.CharField("รหัสชีท", max_length=50, unique=True)
    title = models.CharField("เรื่อง", max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="sheets")

    total_pages = models.PositiveIntegerField("จำนวนหน้า", default=0)
    total_questions = models.PositiveIntegerField("จำนวนข้อ", default=0)  # ถ้าไม่ใช้ ใส่ 0

    is_active = models.BooleanField("เปิดใช้งาน", default=True)

    class Meta:
        verbose_name = "Sheet"
        verbose_name_plural = "Sheets"
        ordering = ("subject__name", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


# -----------------------
# ClassSubject (คลาส/วิชา) - Tutor อัปเดตได้
# (ใช้เป็นฐานของหน้า "Sheet Update" แบบตาราง)
# -----------------------
class ClassSubject(models.Model):
    tutoring_class = models.ForeignKey(TutoringClass, on_delete=models.CASCADE, related_name="class_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="class_subjects")

    current_sheet = models.ForeignKey(
        Sheet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="in_classes",
        verbose_name="ชีทที่กำลังสอน",
    )

    current_page = models.PositiveIntegerField("ถึงหน้า", default=0)
    current_question = models.PositiveIntegerField("ถึงข้อ", default=0)

    # ✅ เพิ่มเพื่อให้ prefill "คนที่สอนครั้งล่าสุด"
    last_teacher = models.CharField("คนที่สอนครั้งล่าสุด", max_length=100, blank=True)

    updated_at = models.DateTimeField(default=timezone.now)
    updated_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)

    is_active = models.BooleanField("เปิดใช้งาน", default=True)

    class Meta:
        verbose_name = "Class Subject"
        verbose_name_plural = "Class Subjects"
        constraints = [
            models.UniqueConstraint(fields=["tutoring_class", "subject"], name="uniq_subject_per_class")
        ]
        ordering = ("tutoring_class__name", "subject__name")

    def __str__(self) -> str:
        return f"{self.tutoring_class} - {self.subject}"

    @property
    def sheet_code(self) -> str:
        return self.current_sheet.code if self.current_sheet_id else ""

    @property
    def sheet_total_pages(self) -> int:
        return int(self.current_sheet.total_pages) if self.current_sheet_id else 0

    def progress_percent(self) -> int:
        """
        ใช้โชว์ % ใน Dashboard:
        - ถ้ามี total_pages: current_page / total_pages
        - ถ้าไม่มี total_pages แต่มี total_questions: current_question / total_questions
        """
        if self.current_sheet and self.current_sheet.total_pages:
            return int((self.current_page / self.current_sheet.total_pages) * 100)
        if self.current_sheet and self.current_sheet.total_questions:
            return int((self.current_question / self.current_sheet.total_questions) * 100)
        return 0


# -----------------------
# Enrollment (การซื้อคอร์สแบบจำนวนครั้ง)
# -----------------------
class Enrollment(models.Model):
    class EnrollmentType(models.TextChoices):
        NORMAL_10 = "normal_10", "ต่อคอร์สปกติ (10 ครั้ง)"
        NORMAL_20 = "normal_20", "ต่อคอร์สปกติ (20 ครั้ง)"
        FIRST_TRIAL_11 = "first_trial_11", "สมัครครั้งแรกแบบทดลองเรียน (11 ครั้ง)"
        FIRST_BONUS_12 = "first_bonus_12", "สมัครครั้งแรกแบบแถม (12 ครั้ง)"
        SPECIAL = "special", "กรณีพิเศษ"

    TYPE_TO_SESSIONS = {
        EnrollmentType.NORMAL_10: 10,
        EnrollmentType.NORMAL_20: 20,
        EnrollmentType.FIRST_TRIAL_11: 11,
        EnrollmentType.FIRST_BONUS_12: 12,
        EnrollmentType.SPECIAL: 10,  # ค่าเริ่มต้นของกรณีพิเศษ (แก้ได้เอง)
    }

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="enrollments")
    tutoring_class = models.ForeignKey(TutoringClass, on_delete=models.PROTECT, related_name="enrollments")

    sale_run_no = models.CharField(
        "เลขที่รายการขายคอร์ส",
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        default=None,
        help_text="ระบบสร้างอัตโนมัติ: {รหัสนักเรียน}-{ลำดับ} เช่น 25001-01",
    )

    enrollment_type = models.CharField(
        "ประเภทการสมัคร",
        max_length=30,
        choices=EnrollmentType.choices,
        default=EnrollmentType.NORMAL_10,
    )

    # snapshot จำนวนครั้ง ณ วันที่สมัคร (กรณีพิเศษแก้เองได้)
    sessions_total = models.IntegerField("จำนวนครั้งทั้งหมด", default=10)

    created_at = models.DateTimeField(default=timezone.now)
    remark = models.TextField("หมายเหตุ", blank=True)

    # ✅ สถานะคอร์ส (จบคอร์ส)
    is_active = models.BooleanField("Active", default=True)

    class CloseReason(models.TextChoices):
        RENEW = "renew", "ต่อคอร์ส"
        NOT_RENEW = "not_renew", "ไม่ต่อคอร์ส"

    closed_reason = models.CharField(
        "ผลการจบคอร์ส",
        max_length=20,
        choices=CloseReason.choices,
        null=True,
        blank=True,
    )
    closed_at = models.DateTimeField("วันที่จบคอร์ส", null=True, blank=True)

    # -----------------------
    # ✅ (A) Payment / Pricing (ตามที่ขอ)
    # -----------------------
    class PaymentType(models.TextChoices):
        FULL = "full", "ชำระเต็ม"
        INSTALLMENT = "installment", "แบ่งชำระ"

    payment_type = models.CharField(
        "รูปแบบการชำระ",
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.FULL,
    )

    installments_count = models.PositiveIntegerField("จำนวนงวด", default=1)

    # ✅ ราคาคอร์ส (snapshot จาก class ตอนสมัคร), ส่วนลด, ราคาสุทธิ
    course_price = models.DecimalField("ราคาคอร์ส (จาก Class)", max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField("ส่วนลด", max_digits=10, decimal_places=2, default=0)
    net_price = models.DecimalField("ราคาสุทธิ", max_digits=10, decimal_places=2, default=0)

    # -----------------------
    # ✅ แจ้งเตือนใกล้ครบคอร์ส
    # -----------------------
    class NotifyMethod(models.TextChoices):
        LINE = "line", "แจ้งทาง Line"
        FACEBOOK = "facebook", "แจ้งทาง FB"
        PAPER = "paper", "แจ้งทางใบ"

    notified_near_complete = models.BooleanField("แจ้งเตือนครบคอร์สแล้ว", default=False)
    notified_method = models.CharField(
        "ช่องทางที่แจ้งเตือน",
        max_length=20,
        choices=NotifyMethod.choices,
        null=True,
        blank=True,
    )
    notified_at = models.DateTimeField("วันที่แจ้งเตือน", null=True, blank=True)

    class Meta:
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        """
        ✅ เพิ่มเลขรายการขายคอร์สอัตโนมัติ (sale_run_no)
        รูปแบบ: {student_code}-{seq} เช่น 25001-01, 25001-02
        """
        is_new = self._state.adding

        # ✅ สร้างเลข run number เฉพาะตอน "เพิ่มใหม่" เท่านั้น
        if is_new and (not self.sale_run_no):
            # ต้องมี student_code ก่อน
            student_code = (self.student.student_code or "").strip() if self.student_id else ""
            if student_code:
                with transaction.atomic():
                    # lock แถวของ enrollment ของนักเรียนคนนี้กันชนกัน
                    last = (
                        Enrollment.objects
                        .select_for_update()
                        .filter(student_id=self.student_id, sale_run_no__startswith=f"{student_code}-")
                        .order_by("-sale_run_no")
                        .values_list("sale_run_no", flat=True)
                        .first()
                    )
                    if not last:
                        seq = 1
                    else:
                        try:
                            seq = int(str(last).split("-")[-1]) + 1
                        except Exception:
                            seq = 1
                    self.sale_run_no = f"{student_code}-{seq:02d}"

        # ตั้งค่า sessions_total อัตโนมัติสำหรับ type ปกติ
        # แต่ถ้าเป็น special ให้คงค่าที่ผู้ใช้กรอกไว้ (ไม่ทับ)
        if self.enrollment_type != self.EnrollmentType.SPECIAL:
            self.sessions_total = self.TYPE_TO_SESSIONS.get(self.enrollment_type, 10)

        # snapshot course_price จาก class (ถ้ายังเป็น 0 หรือยังไม่เคยตั้ง)
        if self.tutoring_class_id and (self.course_price is None or self.course_price == 0):
            self.course_price = self.tutoring_class.course_price or 0

        # normalize installments_count
        if self.payment_type == self.PaymentType.FULL:
            self.installments_count = 1
        else:
            if not self.installments_count or self.installments_count < 1:
                self.installments_count = 1

        # net_price = course_price - discount (กันติดลบ)
        cp = self.course_price or 0
        disc = self.discount_amount or 0
        np = cp - disc
        if np < 0:
            np = 0
        self.net_price = np

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.sale_run_no or '-'} | {self.student.full_name} - {self.tutoring_class.name} - {self.get_enrollment_type_display()}"

    def used_sessions(self) -> int:
        return self.attendances.filter(deducted=True).count()

    def remaining_sessions(self) -> int:
        return self.sessions_total - self.used_sessions()

    def total_hours(self) -> float:
        return float(self.sessions_total * self.tutoring_class.hours_per_session)

    def avg_hours_per_session(self) -> float:
        return float(self.tutoring_class.hours_per_session)

    @property
    def revenue_per_hour(self) -> float:
        """
        ✅ รายได้ต่อชั่วโมง = ราคาสุทธิ / ชั่วโมงรวมของคอร์ส
        """
        th = self.total_hours()
        if th <= 0:
            return 0.0
        return float(self.net_price) / float(th)


# -----------------------
# ✅ Enrollment Installment (งวดชำระ)
# -----------------------
class EnrollmentInstallment(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="installments")
    installment_no = models.PositiveIntegerField("งวดที่", default=1)

    amount_due = models.DecimalField("ยอดงวดนี้", max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField("จ่ายแล้ว", max_digits=10, decimal_places=2, default=0)

    is_paid = models.BooleanField("ชำระครบแล้ว", default=False)
    paid_at = models.DateTimeField("วันที่ชำระ", null=True, blank=True)

    note = models.CharField("หมายเหตุ", max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Enrollment Installment"
        verbose_name_plural = "Enrollment Installments"
        constraints = [
            models.UniqueConstraint(fields=["enrollment", "installment_no"], name="uniq_installment_no_per_enrollment")
        ]
        ordering = ("enrollment_id", "installment_no")

    def __str__(self) -> str:
        return f"{self.enrollment_id} - งวด {self.installment_no}"

    def save(self, *args, **kwargs):
        if (self.amount_paid or 0) >= (self.amount_due or 0) and (self.amount_due or 0) > 0:
            self.is_paid = True
            if not self.paid_at:
                self.paid_at = timezone.now()
        else:
            if (self.amount_due or 0) == 0:
                self.is_paid = False
            elif (self.amount_paid or 0) < (self.amount_due or 0):
                self.is_paid = False
        super().save(*args, **kwargs)


# -----------------------
# Attendance (เช็คชื่อแบบ 3 ปุ่ม)
# -----------------------
class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "มาเรียน (หัก 1 ครั้ง)"
        EXCUSED = "excused", "ลาเรียน (ไม่หักครั้ง)"
        NO_SHOW = "no_show", "ขาดเรียนโดยไม่แจ้ง (หัก 1 ครั้ง)"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="attendances")
    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT, related_name="attendances")

    attendance_date = models.DateField("วันที่เช็คชื่อ", default=timezone.localdate)
    status = models.CharField("สถานะ", max_length=20, choices=Status.choices, default=Status.PRESENT)

    deducted = models.BooleanField("หักครั้ง", default=True)
    checked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Attendance"
        verbose_name_plural = "Attendances"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "enrollment", "attendance_date"],
                name="uniq_attendance_per_student_per_day_per_enrollment",
            )
        ]
        ordering = ("-attendance_date", "-checked_at")

    def save(self, *args, **kwargs):
        self.deducted = self.status in (self.Status.PRESENT, self.Status.NO_SHOW)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.attendance_date} | {self.student.full_name} | {self.status}"


class SheetUpdateEntry(models.Model):
    """
    เก็บความคืบหน้า 'รายวัน' ต่อ (คลาส, วิชา)
    Dashboard จะใช้ record ล่าสุด (date ล่าสุด) เป็นข้อมูลหลัก
    """
    tutoring_class = models.ForeignKey(TutoringClass, on_delete=models.CASCADE, related_name="sheet_updates")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="sheet_updates")

    date = models.DateField("วันที่", default=timezone.localdate)

    sheet = models.ForeignKey(Sheet, on_delete=models.SET_NULL, null=True, blank=True, related_name="sheet_updates")
    page_taught_to = models.PositiveIntegerField("เลขหน้าที่สอนถึง", default=0)
    question_taught_to = models.PositiveIntegerField("เลขข้อที่สอนถึง", default=0)
    last_teacher = models.CharField("คนที่สอนครั้งล่าสุด", max_length=100, blank=True)

    updated_at = models.DateTimeField(default=timezone.now)
    updated_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Sheet Update Entry"
        verbose_name_plural = "Sheet Update Entries"
        constraints = [
            models.UniqueConstraint(fields=["tutoring_class", "subject", "date"], name="uniq_sheet_update_per_day")
        ]
        ordering = ("-date", "tutoring_class__name", "subject__name")

    def progress_percent(self) -> int:
        if self.sheet and self.sheet.total_pages:
            return int((self.page_taught_to / self.sheet.total_pages) * 100)
        if self.sheet and self.sheet.total_questions:
            return int((self.question_taught_to / self.sheet.total_questions) * 100)
        return 0


# -----------------------
# ✅ Sheet Inventory (นับชีทคงเหลือ)
# - 1 Sheet : 1 Inventory record
# - is_finished=True จะย้ายไปอยู่ส่วน "ชีทที่จบแล้ว"
# -----------------------
class SheetInventory(models.Model):
    sheet = models.OneToOneField(Sheet, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.IntegerField("จำนวนคงเหลือ", default=0)

    is_finished = models.BooleanField("จบชีทแล้ว", default=False)
    finished_at = models.DateTimeField("วันที่จบชีท", null=True, blank=True)

    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Sheet Inventory"
        verbose_name_plural = "Sheet Inventories"
        ordering = ("sheet__code",)

    def __str__(self) -> str:
        return f"{self.sheet.code} | {self.quantity}"

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        # กันไม่ให้ quantity ติดลบ
        if self.quantity is None:
            self.quantity = 0
        if self.quantity < 0:
            self.quantity = 0
        # ถ้าทำ finished ให้ set finished_at
        if self.is_finished and not self.finished_at:
            self.finished_at = timezone.now()
        if not self.is_finished:
            self.finished_at = None
        super().save(*args, **kwargs)
