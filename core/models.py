from django.db import models, transaction
from decimal import Decimal
from django.utils import timezone

class School(models.Model):
    name = models.CharField("ชื่อโรงเรียน", max_length=255, unique=True)
    is_active = models.BooleanField("ใช้งาน", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "School"
        verbose_name_plural = "Schools"
        ordering = ["name"]

    def __str__(self):
        return self.name

# -----------------------
# Student
# -----------------------
class Student(models.Model):
    class ContactChannel(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        LINE = "line", "Line"

    class ReferralSource(models.TextChoices):
        REFERRAL = "referral", "คนแนะนำ"
        FACEBOOK = "facebook", "Facebook"
        GOOGLE = "google", "Google"
        FLYER = "flyer", "ใบปลิว"
        WALKIN = "walkin", "เดินผ่าน"

    # -----------------------
    # รหัสนักเรียนอัตโนมัติ: YY + 3 หลัก เช่น 25001
    # -----------------------
    student_code = models.CharField(
        "รหัสนักเรียน",
        max_length=5,
        unique=True,
        blank=True,
        help_text="ระบบสร้างอัตโนมัติรูปแบบ YY### เช่น 25001",
    )

    full_name = models.CharField("ชื่อจริงนามสกุล", max_length=255)
    nickname = models.CharField("ชื่อเล่น", max_length=100, blank=True)

    profile_image = models.ImageField(
        "รูปประจำตัว",
        upload_to="student_profiles/",
        blank=True,
        null=True,
    )

    grade_level = models.CharField("ระดับชั้น", max_length=50, blank=True)
    academic_year = models.CharField("ปีการศึกษา", max_length=20, blank=True)

    # -----------------------
    # ✅ โรงเรียน (ค้นหา / เพิ่มได้)
    # -----------------------
    school = models.ForeignKey(
        School,
        verbose_name="โรงเรียน",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )

    parent_phone = models.CharField("เบอร์ผู้ปกครอง", max_length=50)

    contact_channel = models.CharField(
        "ช่องทางติดต่อ",
        max_length=20,
        choices=ContactChannel.choices,
        default=ContactChannel.LINE,
    )

    enroll_date = models.DateField(
        "วันที่สมัคร",
        default=timezone.localdate,
    )

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

    # -----------------------
    # แสดงชื่อรวม
    # -----------------------
    @property
    def display_name(self) -> str:
        parts = filter(
            None,
            [
                self.student_code,
                self.nickname,
                self.full_name,
                self.grade_level,
                self.school.name if self.school else None,
            ],
        )
        return " | ".join(parts)

    # -----------------------
    # Auto student_code
    # -----------------------
    @staticmethod
    def _next_student_code_for_year(two_digit_year: str) -> str:
        last = (
            Student.objects.filter(student_code__startswith=two_digit_year)
            .order_by("-student_code")
            .values_list("student_code", flat=True)
            .first()
        )
        seq = int(last[-3:]) + 1 if last else 1
        return f"{two_digit_year}{seq:03d}"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.student_code:
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
    class TimeSlot(models.TextChoices):
        SAT_MORNING = "sat_morning", "เสาร์เช้า"
        SAT_AFTERNOON = "sat_afternoon", "เสาร์บ่าย"
        SUN_MORNING = "sun_morning", "อาทิตย์เช้า"
        SUN_AFTERNOON = "sun_afternoon", "อาทิตย์บ่าย"
    
    name = models.CharField("ชื่อคลาส", max_length=100, unique=True)  # เช่น "ป.6 ห้อง A"

    # ✅ เพิ่ม: ราคาคอร์สเต็ม (ใช้ดึงไปใส่ใน Enrollment)
    course_price = models.DecimalField("ราคาคอร์ส (เต็ม)", max_digits=10, decimal_places=2, default=0)

    # ✅ (ข้อ 1) เพิ่ม: ที่นั่งรวม (ต้องกรอกตอนสร้าง Class)
    total_seats = models.PositiveIntegerField(
        "ที่นั่งรวม",
        default=0,
        help_text="จำนวนที่นั่งทั้งหมดของห้องนี้ (ใช้คำนวณ ระหว่างเรียน/ที่นั่งว่าง บน Dashboard)",
    )
    
    time_slot = models.CharField(
        "รอบเวลา",
        max_length=20,
        choices=TimeSlot.choices,
        default=TimeSlot.SAT_MORNING,
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
        EnrollmentType.SPECIAL: 10,
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

    # ✅ ใช้ค่าที่ import / กรอกมา “ตรงตามจริง”
    sessions_total = models.IntegerField("จำนวนครั้งคงเหลือ", default=0)

    created_at = models.DateTimeField(default=timezone.now)
    remark = models.TextField("หมายเหตุ", blank=True)

    # ❗ จะ inactive ก็ต่อเมื่อกดจบคอร์สเท่านั้น
    is_active = models.BooleanField("Active", default=True)

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

    course_price = models.DecimalField("ราคาคอร์ส", max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField("ส่วนลด", max_digits=10, decimal_places=2, default=0)
    net_price = models.DecimalField("ราคาสุทธิ", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        # -----------------------
        # sale_run_no (เฉพาะตอนสร้างใหม่)
        # -----------------------
        if is_new and not self.sale_run_no:
            student_code = (self.student.student_code or "").strip() if self.student_id else ""
            if student_code:
                with transaction.atomic():
                    last = (
                        Enrollment.objects
                        .select_for_update()
                        .filter(
                            student_id=self.student_id,
                            sale_run_no__startswith=f"{student_code}-"
                        )
                        .order_by("-sale_run_no")
                        .values_list("sale_run_no", flat=True)
                        .first()
                    )
                    seq = int(str(last).split("-")[-1]) + 1 if last else 1
                    self.sale_run_no = f"{student_code}-{seq:02d}"

        # -----------------------
        # ❌ ห้าม override sessions_total
        # ใช้ค่าที่ import / กรอกมาเท่านั้น
        # -----------------------
        if self.sessions_total is None:
            self.sessions_total = 0

        # -----------------------
        # ถ้า <= 0 → ใส่หมายเหตุว่า "ครบคอร์ส"
        # (❗ ไม่เปลี่ยน is_active)
        # -----------------------
        if self.sessions_total <= 0:
            auto_note = "ครบคอร์สแล้ว (นำเข้าข้อมูลย้อนหลัง)"
            note = (self.remark or "").strip()
            if auto_note not in note:
                self.remark = f"{note}\n{auto_note}".strip()

        # snapshot course_price
        if self.tutoring_class_id and not self.course_price:
            self.course_price = self.tutoring_class.course_price or 0

        # normalize installments
        if self.payment_type == self.PaymentType.FULL:
            self.installments_count = 1
        elif not self.installments_count or self.installments_count < 1:
            self.installments_count = 1

        # net_price
        cp = self.course_price or 0
        disc = self.discount_amount or 0
        self.net_price = max(cp - disc, 0)

        super().save(*args, **kwargs)

    def used_sessions(self):
        return self.attendances.filter(deducted=True).count()

    @property
    def remaining_sessions(self):
        return self.sessions_total - self.used_sessions()


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

# -----------------------
# ✅ Admission Inquiry (สมัครเรียน / จองทดลองเรียน)
# -----------------------
class AdmissionInquiry(models.Model):
    class RequestType(models.TextChoices):
        TRIAL = "trial", "จองทดลองเรียน"
        ENROLL = "enroll", "สมัครเรียน"
        QUEUE = "queue", "จองที่นั่งล่วงหน้า"

    class GradeLevel(models.TextChoices):
        P4 = "p4", "ป.4"
        P5 = "p5", "ป.5"
        P6 = "p6", "ป.6"
        M1 = "m1", "ม.1"
        M2 = "m2", "ม.2"
        M3 = "m3", "ม.3"
        M4 = "m4", "ม.4"

    class PreferredTimeSlot(models.TextChoices):
        SAT_MORNING = "sat_morning", "เสาร์เช้า (08.30-12.30)"
        SAT_AFTERNOON = "sat_afternoon", "เสาร์บ่าย (13.30-17.30)"
        SUN_MORNING = "sun_morning", "อาทิตย์เช้า (08.30-12.30)"
        SUN_AFTERNOON = "sun_afternoon", "อาทิตย์บ่าย (13.30-17.30)"

    class TrialAttended(models.TextChoices):
        PENDING = "pending", "ยังไม่ระบุ"
        YES = "yes", "มาเรียนจริง"
        NO = "no", "ไม่ได้มาเรียน"

    class TrialResult(models.TextChoices):
        PENDING = "pending", "ยังไม่ระบุ"
        ENROLLED = "enrolled", "ทดลองแล้วสมัครต่อ"
        NOT_ENROLLED = "not_enrolled", "ทดลองแล้วไม่สมัคร"
        FOLLOW_UP = "follow_up", "รอติดตามผล"

    request_type = models.CharField(
        "ประเภทการลงทะเบียน",
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.TRIAL,
    )

    nickname = models.CharField("ชื่อเล่น", max_length=100)
    first_name = models.CharField("ชื่อจริง", max_length=150)
    last_name = models.CharField("นามสกุล", max_length=150)
    school_name = models.CharField("โรงเรียน", max_length=255, blank=True)
    contact_phone = models.CharField("เบอร์ติดต่อ", max_length=50)
    latest_gpa = models.DecimalField(
        "เกรดเฉลี่ยเทอมล่าสุด",
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )

    first_lesson_date = models.DateField("วันที่ทดลองเรียน/เริ่มเรียนวันแรก")
    grade_level = models.CharField(
        "ระดับชั้น",
        max_length=20,
        choices=GradeLevel.choices,
    )
    preferred_time_slot = models.CharField(
        "รอบเวลาเรียน",
        max_length=30,
        choices=PreferredTimeSlot.choices,
    )

    sheet_prepared = models.BooleanField("เตรียมชีทพร้อมแล้ว", default=False)
    trial_attended = models.CharField(
        "มาเรียนจริงหรือไม่",
        max_length=20,
        choices=TrialAttended.choices,
        default=TrialAttended.PENDING,
        help_text="ใช้สำหรับรายการจองทดลองเรียน",
    )
    trial_result = models.CharField(
        "ผลหลังทดลองเรียน",
        max_length=20,
        choices=TrialResult.choices,
        default=TrialResult.PENDING,
        help_text="ใช้สำหรับรายการจองทดลองเรียน",
    )
    internal_note = models.TextField("หมายเหตุภายใน", blank=True)

    created_at = models.DateTimeField("วันที่ลงทะเบียน", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Admission Inquiry"
        verbose_name_plural = "Admission Inquiries"
        ordering = ("-created_at",)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return f"{self.get_request_type_display()} | {self.nickname} | {self.full_name}"

# =========================================================
# ✅ School Finance / Overview Modules
# =========================================================
class FinanceSetting(models.Model):
    key = models.CharField("Key", max_length=80, unique=True)
    value = models.DecimalField("Value", max_digits=12, decimal_places=2, default=0)
    description = models.CharField("Description", max_length=255, blank=True)
    updated_at = models.DateTimeField("Updated at", auto_now=True)

    class Meta:
        verbose_name = "Finance Setting"
        verbose_name_plural = "Finance Settings"
        ordering = ("key",)

    def __str__(self) -> str:
        return f"{self.key}: {self.value}"


class ExpenseCategory(models.Model):
    name = models.CharField("ประเภทค่าใช้จ่าย", max_length=120, unique=True)
    is_tutor_payroll = models.BooleanField("เป็นค่าจ้างติวเตอร์", default=False)
    is_active = models.BooleanField("ใช้งาน", default=True)
    sort_order = models.PositiveIntegerField("ลำดับ", default=0)

    class Meta:
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"
        ordering = ("sort_order", "name")

    def __str__(self) -> str:
        return self.name


class SchoolExpense(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "เงินสด"
        TRANSFER = "transfer", "โอนเงิน"
        QR = "qr", "QR / PromptPay"
        CARD = "card", "บัตร"
        OTHER = "other", "อื่น ๆ"

    expense_date = models.DateField("วันที่จ่าย", default=timezone.localdate)
    category = models.ForeignKey(
        ExpenseCategory,
        verbose_name="ประเภทค่าใช้จ่าย",
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    vendor = models.CharField("Vendor / ผู้รับเงิน", max_length=255, blank=True)
    description = models.CharField("รายละเอียด", max_length=255, blank=True)
    amount = models.DecimalField("จำนวนเงิน", max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        "วิธีจ่าย",
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.TRANSFER,
    )
    note = models.TextField("หมายเหตุ", blank=True)
    created_at = models.DateTimeField("วันที่บันทึก", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "School Expense"
        verbose_name_plural = "School Expenses"
        ordering = ("-expense_date", "-created_at")

    def __str__(self) -> str:
        return f"{self.expense_date} | {self.category} | {self.amount:,.2f}"


class Tutor(models.Model):
    name = models.CharField("ชื่อติวเตอร์", max_length=120, unique=True)
    phone = models.CharField("เบอร์ติดต่อ", max_length=50, blank=True)
    note = models.TextField("หมายเหตุ", blank=True)
    is_active = models.BooleanField("ใช้งาน", default=True)
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Tutor"
        verbose_name_plural = "Tutors"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class TutorPayrollEntry(models.Model):
    work_date = models.DateField("วันที่สอน", default=timezone.localdate)
    tutor = models.ForeignKey(
        Tutor,
        verbose_name="ติวเตอร์",
        on_delete=models.PROTECT,
        related_name="payroll_entries",
    )
    teaching_hours = models.DecimalField("จำนวนชั่วโมงสอน", max_digits=5, decimal_places=2, default=0)
    hourly_rate = models.DecimalField("เรทต่อชั่วโมง", max_digits=10, decimal_places=2, default=0)
    teaching_fee = models.DecimalField("ค่าสอน", max_digits=12, decimal_places=2, default=0)
    travel_fee = models.DecimalField("ค่าเดินทาง", max_digits=12, decimal_places=2, default=0)
    idle_fee = models.DecimalField("ค่านั่งว่าง / ค่าอื่น ๆ", max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField("ยอดรวม", max_digits=12, decimal_places=2, default=0)
    note = models.TextField("หมายเหตุ", blank=True)
    created_at = models.DateTimeField("วันที่บันทึก", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Tutor Payroll Entry"
        verbose_name_plural = "Tutor Payroll Entries"
        ordering = ("-work_date", "tutor__name")
        constraints = [
            models.UniqueConstraint(fields=["work_date", "tutor"], name="uniq_tutor_payroll_per_day")
        ]

    @staticmethod
    def calculate_hourly_rate(hours: Decimal) -> Decimal:
        hours = Decimal(str(hours or 0))
        if hours <= 0:
            return Decimal("0")
        if hours <= 1:
            return Decimal("550")
        if hours < 4:
            return Decimal("350")
        return Decimal("300")

    @staticmethod
    def calculate_travel_fee(hours: Decimal) -> Decimal:
        hours = Decimal(str(hours or 0))
        if hours <= 0:
            return Decimal("0")
        if hours <= 1:
            return Decimal("200")
        if hours < 4:
            return Decimal("150")
        return Decimal("100")

    def recalculate(self):
        hours = Decimal(str(self.teaching_hours or 0))
        self.hourly_rate = self.calculate_hourly_rate(hours)
        self.teaching_fee = hours * self.hourly_rate
        self.travel_fee = self.calculate_travel_fee(hours)
        self.idle_fee = Decimal(str(self.idle_fee or 0))
        self.total_amount = self.teaching_fee + self.travel_fee + self.idle_fee

    def save(self, *args, **kwargs):
        self.recalculate()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.work_date} | {self.tutor} | {self.total_amount:,.2f}"
