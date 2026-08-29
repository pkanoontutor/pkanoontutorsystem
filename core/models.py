import re
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
    class GradeLevel(models.TextChoices):
        P4 = "p4", "ป.4"
        P5 = "p5", "ป.5"
        P6 = "p6", "ป.6"
        M1 = "m1", "ม.1"
        M2 = "m2", "ม.2"
        M3 = "m3", "ม.3"
        M4 = "m4", "ม.4"
        M5 = "m5", "ม.5"

    code = models.CharField("รหัสชีท", max_length=50, unique=True)
    title = models.CharField("เรื่อง", max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="sheets")
    grade_level = models.CharField(
        "ระดับชั้น",
        max_length=20,
        choices=GradeLevel.choices,
        blank=True,
        default="",
        help_text="ใช้จัดกลุ่มชีทใน Sheet Inventory และช่วย filter ชีทให้ตรงกับ class",
    )

    total_pages = models.PositiveIntegerField(
        "จำนวนหน้า",
        default=0,
        help_text="จำนวนหน้าของไฟล์เนื้อหา ใช้คำนวณ % ความคืบหน้าการสอนในหน้าอัปเดตติวเตอร์",
    )
    total_questions = models.PositiveIntegerField("จำนวนข้อ", default=0)  # ถ้าไม่ใช้ ใส่ 0

    cover_image = models.ImageField(
        "รูปหน้าปก",
        upload_to="sheet_covers/",
        blank=True,
        null=True,
        help_text="วางรูป (Ctrl+V) หรืออัปโหลดได้จากหน้า Sheet Inventory",
    )

    source_book = models.ForeignKey(
        "Book",
        verbose_name="สร้างจากหนังสือเล่ม",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sheets",
        help_text="ใช้อ้างอิงย้อนหลังว่าชีทนี้ทำมาจากหนังสือเล่มไหน",
    )

    is_active = models.BooleanField("เปิดใช้งาน", default=True)

    class Meta:
        verbose_name = "Sheet"
        verbose_name_plural = "Sheets"
        ordering = ("grade_level", "subject__name", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


# -----------------------
# Book (คลังหนังสือ) - หนังสือต้นทางที่ใช้ทำชีท
# -----------------------
class Book(models.Model):
    """A source book the school builds its sheets from.

    Only the cover image is uploaded here; the book file itself lives
    elsewhere and is referenced by link, since scanned books are far too
    large to keep on the app's disk.
    """

    class AnswerLocation(models.TextChoices):
        INCLUDED = "included", "รวมเฉลยในเล่ม"
        SEPARATE = "separate", "มีเฉลยแยกเล่ม"

    code = models.CharField("รหัสหนังสือ", max_length=50, unique=True)
    title = models.CharField("ชื่อหนังสือ", max_length=255)
    subject = models.ForeignKey(
        Subject,
        verbose_name="วิชา",
        on_delete=models.PROTECT,
        related_name="books",
        null=True,
        blank=True,
    )
    grade_level = models.CharField(
        "ระดับชั้น",
        max_length=20,
        choices=Sheet.GradeLevel.choices,
        blank=True,
        default="",
    )
    file_url = models.URLField("ลิงก์ไฟล์หนังสือ", max_length=2000, blank=True)
    answer_location = models.CharField(
        "เฉลย",
        max_length=20,
        choices=AnswerLocation.choices,
        default=AnswerLocation.INCLUDED,
    )
    answer_url = models.URLField(
        "ลิงก์ไฟล์เฉลย",
        max_length=2000,
        blank=True,
        help_text="ใช้เมื่อเลือก 'มีเฉลยแยกเล่ม'",
    )
    cover_image = models.ImageField(
        "รูปปก",
        upload_to="book_covers/",
        blank=True,
        null=True,
        help_text="อัปโหลด JPG หรือ PNG ใช้เป็นรูปประจำหนังสือเล่มนี้",
    )
    note = models.TextField("หมายเหตุ", blank=True)
    is_active = models.BooleanField("ใช้งาน", default=True)
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ("grade_level", "subject__name", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


# -----------------------
# SheetDocument (ไฟล์ PDF ของชีท: ปก / เนื้อหา / เฉลย)
# -----------------------
class SheetDocument(models.Model):
    """A PDF attached to a sheet.

    A sheet has at most one cover but may have several content and answer
    files, so they all live in one table keyed by `kind` rather than as
    separate fields on Sheet. The cover also carries a PNG thumbnail
    rendered from page 1 in the browser at upload time, so the tutor
    bookshelf can show covers without rendering a PDF per tile.
    """

    class Kind(models.TextChoices):
        COVER = "cover", "ปก"
        CONTENT = "content", "เนื้อหา"
        ANSWER = "answer", "เฉลย"

    sheet = models.ForeignKey(
        Sheet,
        verbose_name="ชีท",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    kind = models.CharField("ประเภทไฟล์", max_length=20, choices=Kind.choices)
    title = models.CharField(
        "ชื่อไฟล์ที่แสดง",
        max_length=255,
        blank=True,
        help_text="เว้นว่างได้ ระบบจะใช้ชื่อไฟล์เดิม",
    )
    pdf = models.FileField("ไฟล์ PDF", upload_to="sheet_documents/")
    thumbnail = models.ImageField(
        "รูปย่อหน้าแรก",
        upload_to="sheet_doc_thumbs/",
        blank=True,
        null=True,
        help_text="สร้างอัตโนมัติจากหน้าแรกของ PDF ตอนอัปโหลด",
    )
    page_count = models.PositiveIntegerField("จำนวนหน้า", default=0)
    source_book = models.ForeignKey(
        Book,
        verbose_name="มาจากหนังสือเล่ม",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sheet_documents",
    )
    source_url = models.URLField("ลิงก์อ้างอิง", max_length=2000, blank=True)
    display_order = models.PositiveIntegerField("ลำดับ", default=1)
    uploaded_by = models.ForeignKey(
        "auth.User",
        verbose_name="ผู้อัปโหลด",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sheet_documents",
    )
    created_at = models.DateTimeField("วันที่อัปโหลด", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Sheet Document"
        verbose_name_plural = "Sheet Documents"
        ordering = ("sheet__code", "kind", "display_order", "id")

    def __str__(self) -> str:
        return f"{self.sheet.code} | {self.get_kind_display()} | {self.display_name}"

    @property
    def display_name(self) -> str:
        if self.title:
            return self.title
        name = (self.pdf.name or "").rsplit("/", 1)[-1]
        return name or self.get_kind_display()


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
# Course Payment / Receipt
# -----------------------
class CoursePayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "เงินสด"
        BANK_TRANSFER = "bank_transfer", "โอนธนาคาร"
        PROMPTPAY = "promptpay", "PromptPay"
        CREDIT_CARD = "credit_card", "บัตรเครดิต"

    class PaymentType(models.TextChoices):
        FULL = "full", "ชำระเต็ม"
        INSTALLMENT = "installment", "แบ่งชำระ"

    class EnrollmentAction(models.TextChoices):
        NEW = "new", "สร้าง Enrollment ใหม่"
        ADD_EXISTING = "add_existing", "เพิ่มจำนวนครั้งเข้า Enrollment เดิม"

    class ReceiptStatus(models.TextChoices):
        ISSUED = "issued", "ออกใบเสร็จแล้ว"
        CANCELLED = "cancelled", "ยกเลิก"

    class ReceiptKind(models.TextChoices):
        COURSE = "course", "ค่าคอร์สเรียน"
        OTHER = "other", "รายการอื่น (ไม่ผูกกับคอร์ส)"

    receipt_no = models.CharField(
        "เลขที่ใบเสร็จ",
        max_length=20,
        unique=True,
        blank=True,
        help_text="ระบบสร้างอัตโนมัติรูปแบบ YYMM-001",
    )
    payment_date = models.DateField("วันที่รับเงิน", default=timezone.localdate)

    receipt_kind = models.CharField(
        "ประเภทใบเสร็จ",
        max_length=20,
        choices=ReceiptKind.choices,
        default=ReceiptKind.COURSE,
    )
    item_description = models.CharField(
        "รายการ (สำหรับใบเสร็จที่ไม่ผูกกับคอร์ส)",
        max_length=200,
        blank=True,
        help_text="เช่น ค่าชีทสำหรับทดลองเรียน",
    )

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="course_payments")
    tutoring_class = models.ForeignKey(
        TutoringClass,
        on_delete=models.PROTECT,
        related_name="course_payments",
        null=True,
        blank=True,
        help_text="เว้นว่างได้สำหรับใบเสร็จประเภทรายการอื่นที่ไม่ผูกกับคอร์ส/Enrollment",
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="course_payments",
        null=True,
        blank=True,
    )

    enrollment_action = models.CharField(
        "การจัดการ Enrollment",
        max_length=20,
        choices=EnrollmentAction.choices,
        default=EnrollmentAction.NEW,
    )
    enrollment_created = models.BooleanField("สร้าง Enrollment ใหม่จากใบเสร็จนี้", default=False)
    enrollment_sessions_before = models.IntegerField("จำนวนครั้งก่อนเพิ่ม", null=True, blank=True)

    session_package = models.CharField("แพ็กเกจจำนวนครั้ง", max_length=30, default="10")
    sessions_granted = models.PositiveIntegerField("จำนวนครั้งที่ให้เรียน", default=10)

    course_price = models.DecimalField("ราคาคอร์ส", max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField("ส่วนลด", max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField("ราคาสุทธิ", max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField("ยอดรับชำระ", max_digits=10, decimal_places=2, default=0)

    payment_type = models.CharField(
        "รูปแบบการชำระ",
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.FULL,
    )
    payment_method = models.CharField(
        "วิธีชำระเงิน",
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
    )

    status = models.CharField(
        "สถานะใบเสร็จ",
        max_length=20,
        choices=ReceiptStatus.choices,
        default=ReceiptStatus.ISSUED,
    )
    note = models.TextField("หมายเหตุ", blank=True)

    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_course_payments",
    )
    created_at = models.DateTimeField("วันที่บันทึก", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    cancelled_at = models.DateTimeField("วันที่ยกเลิก", null=True, blank=True)
    cancelled_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_course_payments",
    )
    cancel_reason = models.TextField("เหตุผลการยกเลิก", blank=True)

    class Meta:
        verbose_name = "Course Payment / Receipt"
        verbose_name_plural = "Course Payments / Receipts"
        ordering = ("-payment_date", "-created_at")

    def __str__(self) -> str:
        return f"{self.receipt_no or '-'} | {self.student} | {self.amount_paid}"

    @staticmethod
    def _next_receipt_no_for_month(prefix: str) -> str:
        last = (
            CoursePayment.objects
            .filter(receipt_no__startswith=f"{prefix}-")
            .order_by("-receipt_no")
            .values_list("receipt_no", flat=True)
            .first()
        )
        if last:
            try:
                seq = int(str(last).split("-")[-1]) + 1
            except Exception:
                seq = 1
        else:
            seq = 1
        return f"{prefix}-{seq:03d}"

    def save(self, *args, **kwargs):
        if not self.net_amount:
            self.net_amount = max((self.course_price or 0) - (self.discount_amount or 0), Decimal("0"))

        if not self.amount_paid:
            self.amount_paid = self.net_amount

        if not self.receipt_no:
            pay_date = self.payment_date or timezone.localdate()
            prefix = pay_date.strftime("%y%m")
            with transaction.atomic():
                self.receipt_no = CoursePayment._next_receipt_no_for_month(prefix)
                super().save(*args, **kwargs)
            return

        super().save(*args, **kwargs)

    @property
    def is_cancelled(self) -> bool:
        return self.status == self.ReceiptStatus.CANCELLED

    @property
    def receipt_student_name(self) -> str:
        return self.student.display_name if self.student_id else "-"


# -----------------------
# Promotions: เพื่อนชวนเพื่อน (friend-refers-friend)
# -----------------------
class FriendReferral(models.Model):
    """One successful referral: `referrer` brought in `referred_student`.

    credit_amount is fixed at creation time (100 THB for the referrer's first
    ever referral, 50 THB for every one after that) so the promo's payout rule
    can change later without rewriting history.
    """

    referrer = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="referrals_made",
        verbose_name="ผู้ชวน",
    )
    referred_student = models.ForeignKey(
        Student, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="referred_by_entries", verbose_name="ผู้ถูกชวน (นักเรียนใหม่)",
    )
    receipt = models.ForeignKey(
        CoursePayment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="friend_referrals", verbose_name="ใบเสร็จของนักเรียนใหม่ที่บันทึกการชวนนี้",
    )
    credit_amount = models.DecimalField(
        "มูลค่าเครดิตที่ผู้ชวนได้รับ", max_digits=10, decimal_places=2, default=0,
    )
    created_at = models.DateTimeField("วันที่ชวนสำเร็จ", default=timezone.now)

    class Meta:
        verbose_name = "Friend Referral"
        verbose_name_plural = "Friend Referrals"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.referrer} ชวน {self.referred_student or '-'} (+{self.credit_amount:.0f}฿)"


# -----------------------
# Course Renewal Notice
# -----------------------
class CourseRenewalNotice(models.Model):
    """
    ใบแจ้งการต่อคอร์ส / ใบแจ้งชำระงวดถัดไป:
    สร้างจาก Enrollment และเก็บประวัติใบแจ้งที่เคยสร้างไว้
    """

    class NoticeType(models.TextChoices):
        RENEWAL = "renewal", "ใบแจ้งต่อคอร์ส"
        INSTALLMENT = "installment", "ใบแจ้งชำระงวดที่ 2/3/4"

    notice_type = models.CharField(
        "ประเภทใบแจ้ง",
        max_length=20,
        choices=NoticeType.choices,
        default=NoticeType.RENEWAL,
    )

    enrollment = models.ForeignKey(
        Enrollment,
        verbose_name="Enrollment",
        on_delete=models.PROTECT,
        related_name="renewal_notices",
    )
    student = models.ForeignKey(
        Student,
        verbose_name="นักเรียน",
        on_delete=models.PROTECT,
        related_name="renewal_notices",
    )
    tutoring_class = models.ForeignKey(
        TutoringClass,
        verbose_name="คอร์ส/คลาส",
        on_delete=models.PROTECT,
        related_name="renewal_notices",
    )

    source_payment = models.ForeignKey(
        CoursePayment,
        verbose_name="ใบเสร็จอ้างอิง / งวดแรก",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="renewal_notices",
        help_text="ใช้กับใบแจ้งชำระงวดถัดไป เพื่ออ้างอิงใบเสร็จงวดแรกหรือรายการที่เกี่ยวข้อง",
    )

    expected_course_end_date = models.DateField("วันที่คาดว่าจะครบคอร์ส")
    next_course_start_date = models.DateField("วันที่เริ่มต้นคอร์สใหม่")

    package_10_full_price = models.DecimalField("10 สัปดาห์ - ราคาเต็ม", max_digits=10, decimal_places=2, default=3990)
    package_10_discount = models.DecimalField("10 สัปดาห์ - ส่วนลด", max_digits=10, decimal_places=2, default=100)
    package_10_net_price = models.DecimalField("10 สัปดาห์ - ราคาสุทธิ", max_digits=10, decimal_places=2, default=3890)

    package_20_full_price = models.DecimalField("20 สัปดาห์ - ราคาเต็ม", max_digits=10, decimal_places=2, default=7980)
    package_20_discount = models.DecimalField("20 สัปดาห์ - ส่วนลด", max_digits=10, decimal_places=2, default=500)
    package_20_net_price = models.DecimalField("20 สัปดาห์ - ราคาสุทธิ", max_digits=10, decimal_places=2, default=7480)

    package_30_full_price = models.DecimalField("30 สัปดาห์ - ราคาเต็ม", max_digits=10, decimal_places=2, default=11970)
    package_30_discount = models.DecimalField("30 สัปดาห์ - ส่วนลด", max_digits=10, decimal_places=2, default=1000)
    package_30_net_price = models.DecimalField("30 สัปดาห์ - ราคาสุทธิ", max_digits=10, decimal_places=2, default=10970)

    installment_full_amount = models.DecimalField(
        "แบ่งชำระ - ยอดเต็ม",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="ยอดเต็มของคอร์ส ใช้กับใบแจ้งชำระงวดถัดไป",
    )
    installment_paid_amount = models.DecimalField(
        "แบ่งชำระ - ชำระแล้ว",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="ยอดที่ชำระแล้ว ใช้กับใบแจ้งชำระงวดถัดไป",
    )
    installment_remaining_amount = models.DecimalField(
        "แบ่งชำระ - ยอดคงเหลือ",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="ยอดคงเหลือ ระบบคำนวณจากยอดเต็ม - ชำระแล้ว แต่ยังสามารถแก้ยอดเต็ม/ชำระแล้วก่อนบันทึกได้",
    )

    installment_no = models.PositiveSmallIntegerField(
        "งวดที่แจ้งชำระ",
        null=True,
        blank=True,
        choices=((2, "งวดที่ 2"), (3, "งวดที่ 3"), (4, "งวดที่ 4")),
        help_text="ใช้กับใบแจ้งชำระงวดที่ 2/3/4",
    )
    installment_sessions = models.PositiveIntegerField(
        "จำนวนครั้งที่ให้เรียนจากงวดนี้",
        default=0,
        help_text="กรอกเองสำหรับใบแจ้งชำระงวดที่ 2/3/4",
    )

    note_wording = models.TextField(
        "ข้อความท้ายใบแจ้ง",
        default="ผู้ปกครองสามารถขอชะลอจ่าย เลื่อนจ่ายเป็นสิ้นเดือนได้โดยนักเรียนไม่ต้องเว้นวรรคการเรียนครับ ติดต่อแจ้งพี่ขนุนทาง Line @ ครับ",
    )

    referral_credit_used = models.DecimalField(
        "ใช้เครดิตชวนเพื่อนเป็นส่วนลด", max_digits=10, decimal_places=2, default=0,
        help_text="หักออกจากราคาสุทธิของทุกแพ็กเกจ/ยอดคงเหลือในใบแจ้งนี้ ไม่เกินเครดิตคงเหลือของนักเรียนคนนี้",
    )

    hide_from_quick_receipt_pick = models.BooleanField(
        "ซ่อนจากการ์ดลัดในหน้าออกใบเสร็จ", default=False,
        help_text="ติ๊กเมื่อกดกากบาทลบการ์ดนี้ออกจากรายการลัดในหน้าออกใบเสร็จ (ไม่ได้ลบใบแจ้งจริง)",
    )

    is_sent_to_parent = models.BooleanField("ส่งแจ้งผู้ปกครองแล้ว", default=False)
    sent_to_parent_at = models.DateTimeField("วันที่ส่งแจ้งผู้ปกครอง", null=True, blank=True)
    sent_to_parent_by = models.ForeignKey(
        "auth.User",
        verbose_name="ผู้กดส่งแจ้ง",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_course_renewal_notices",
    )

    created_by = models.ForeignKey(
        "auth.User",
        verbose_name="ผู้สร้าง",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_course_renewal_notices",
    )
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Course Renewal Notice"
        verbose_name_plural = "Course Renewal Notices"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.get_notice_type_display()} | {self.student} | {self.tutoring_class} | {self.expected_course_end_date}"

    def save(self, *args, **kwargs):
        credit = Decimal(str(self.referral_credit_used or 0))
        self.package_10_net_price = max((self.package_10_full_price or 0) - (self.package_10_discount or 0) - credit, Decimal("0"))
        self.package_20_net_price = max((self.package_20_full_price or 0) - (self.package_20_discount or 0) - credit, Decimal("0"))
        self.package_30_net_price = max((self.package_30_full_price or 0) - (self.package_30_discount or 0) - credit, Decimal("0"))

        if self.notice_type == self.NoticeType.INSTALLMENT:
            self.installment_remaining_amount = max(
                (self.installment_full_amount or 0) - (self.installment_paid_amount or 0) - credit,
                Decimal("0"),
            )
            if not self.installment_no:
                self.installment_no = 2
        else:
            self.installment_no = None
            self.installment_sessions = 0

        super().save(*args, **kwargs)

    @property
    def remaining_sessions_snapshot(self) -> int:
        try:
            return int(self.enrollment.remaining_sessions)
        except Exception:
            return 0


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
    minimum_stock = models.PositiveIntegerField(
        "ขั้นต่ำที่ควรมี",
        default=0,
        help_text="ใช้สำหรับเตือนชีทใกล้หมด",
    )

    target_stock = models.PositiveIntegerField(
        "จำนวนที่ต้องการมีในคลัง",
        default=0,
        help_text="ใช้คำนวณจำนวนที่ควรสั่งปรินท์เพิ่ม",
    )
    onedrive_url = models.URLField(
        "ลิงก์ไฟล์ OneDrive",
        max_length=2000,
        blank=True,
        help_text="ลิงก์ไฟล์ชีทสำหรับส่งร้านปรินท์",
    )
    storage_location = models.CharField(
        "ตำแหน่งวางชีท",
        max_length=120,
        blank=True,
        help_text="ตำแหน่งที่วางชีทจริงในห้องเก็บของ เช่น ชั้น 2 ฝั่งซ้าย / กล่อง A3 — ให้คนนับชีทกรอกไว้หาง่าย",
    )

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


class SheetInventoryMovement(models.Model):
    class MovementType(models.TextChoices):
        ADD = "add", "เพิ่ม stock"
        DEDUCT = "deduct", "ตัด stock"
        SET = "set", "ตั้งยอดจริง"
        COUNT = "count", "นับ stock"

    sheet = models.ForeignKey(
        Sheet,
        verbose_name="ชีท",
        on_delete=models.PROTECT,
        related_name="inventory_movements",
    )
    movement_type = models.CharField(
        "ประเภท movement",
        max_length=20,
        choices=MovementType.choices,
    )
    quantity = models.PositiveIntegerField("จำนวน", default=0)
    balance_before = models.IntegerField("ยอดก่อนทำรายการ", default=0)
    balance_after = models.IntegerField("ยอดหลังทำรายการ", default=0)
    note = models.CharField("หมายเหตุ", max_length=255, blank=True)
    created_by = models.ForeignKey(
        "auth.User",
        verbose_name="ผู้บันทึก",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sheet_inventory_movements",
    )
    created_at = models.DateTimeField("วันที่บันทึก", default=timezone.now)

    class Meta:
        verbose_name = "Sheet Inventory Movement"
        verbose_name_plural = "Sheet Inventory Movements"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.sheet.code} | {self.get_movement_type_display()} | {self.quantity}"


class SheetPrintOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "รอปรินท์"
        READY = "ready", "ปรินท์เสร็จแล้วพร้อมส่ง"
        RECEIVED = "received", "ตรวจรับเข้าคลังแล้ว"

    class BindingType(models.TextChoices):
        CORNER = "corner", "เย็บมุม"
        SIDE = "side", "เย็บข้าง"

    class SpineColor(models.TextChoices):
        BLUE = "blue", "สีฟ้า"
        RED = "red", "สีแดง"
        PINK = "pink", "สีชมพู"
        GREEN = "green", "สีเขียว"
        ORANGE = "orange", "สีส้ม"

    sheet = models.ForeignKey(
        Sheet,
        verbose_name="ชีท",
        on_delete=models.PROTECT,
        related_name="print_orders",
        null=True,
        blank=True,
        help_text="เว้นว่างได้สำหรับรายการเอกสารอื่นที่ไม่ใช่ชีทใน Sheet Inventory",
    )
    custom_title = models.CharField(
        "ชื่อเอกสารอื่น",
        max_length=255,
        blank=True,
        help_text="ใช้กรณีสั่งปรินท์เอกสารที่ไม่ได้อยู่ใน Sheet Inventory",
    )
    quantity = models.PositiveIntegerField("จำนวนที่สั่งปรินท์", default=1)
    printed_quantity = models.PositiveIntegerField("จำนวนที่ร้านปรินท์เสร็จแล้ว", default=0)
    print_done = models.BooleanField("ปรินท์แล้ว", default=False)
    bound_done = models.BooleanField("เย็บแล้ว", default=False)
    spine_unavailable = models.BooleanField("สันรูดหมด / รอสันรูด", default=False)
    due_date = models.DateField("วันที่ต้องส่ง", null=True, blank=True)
    onedrive_url = models.URLField("ลิงก์ไฟล์ OneDrive", max_length=2000, blank=True)
    binding_type = models.CharField(
        "ประเภทการเย็บ",
        max_length=20,
        choices=BindingType.choices,
        default=BindingType.SIDE,
    )
    spine_color = models.CharField(
        "สีสันรูด",
        max_length=20,
        choices=SpineColor.choices,
        blank=True,
        default="",
        help_text="ใช้เฉพาะกรณีเย็บข้าง",
    )
    note = models.TextField("หมายเหตุ", blank=True)
    status = models.CharField(
        "สถานะ",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    requested_by = models.ForeignKey(
        "auth.User",
        verbose_name="ผู้สั่งปรินท์",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sheet_print_orders",
    )
    created_at = models.DateTimeField("วันที่สั่ง", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)
    completed_at = models.DateTimeField("วันที่ร้านกดเสร็จแล้ว", null=True, blank=True)
    received_at = models.DateTimeField("วันที่ตรวจรับเข้าคลัง", null=True, blank=True)
    received_by = models.ForeignKey(
        "auth.User",
        verbose_name="ผู้ตรวจรับ",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_sheet_print_orders",
    )

    class Meta:
        verbose_name = "Sheet Print Order"
        verbose_name_plural = "Sheet Print Orders"
        ordering = ("status", "due_date", "created_at")

    def __str__(self) -> str:
        return f"{self.display_code} | {self.quantity} | {self.get_status_display()}"

    @property
    def is_custom_document(self) -> bool:
        return self.sheet_id is None

    @property
    def display_code(self) -> str:
        return self.sheet.code if self.sheet_id else "DOC"

    @property
    def display_title(self) -> str:
        if self.sheet_id:
            return self.sheet.title
        return self.custom_title or "เอกสารส่งปรินท์"

    @property
    def subject_name(self) -> str:
        if self.sheet_id and self.sheet.subject_id:
            return self.sheet.subject.name
        return "เอกสารอื่น"

    @property
    def binding_label(self) -> str:
        return self.get_binding_type_display()

    @property
    def spine_color_label(self) -> str:
        if self.binding_type == self.BindingType.CORNER:
            return "-"
        return self.get_spine_color_display() if self.spine_color else "ไม่ระบุสี"

    @property
    def spine_color_bg(self) -> str:
        if self.binding_type == self.BindingType.CORNER:
            return "#ffffff"
        return {
            self.SpineColor.BLUE: "#dbeafe",
            self.SpineColor.RED: "#fee2e2",
            self.SpineColor.PINK: "#fce7f3",
            self.SpineColor.GREEN: "#dcfce7",
            self.SpineColor.ORANGE: "#ffedd5",
        }.get(self.spine_color, "#ffffff")

    @property
    def spine_color_border(self) -> str:
        if self.binding_type == self.BindingType.CORNER:
            return "#e2e8f0"
        return {
            self.SpineColor.BLUE: "#93c5fd",
            self.SpineColor.RED: "#fca5a5",
            self.SpineColor.PINK: "#f9a8d4",
            self.SpineColor.GREEN: "#86efac",
            self.SpineColor.ORANGE: "#fdba74",
        }.get(self.spine_color, "#e2e8f0")

    @property
    def printed_remaining(self) -> int:
        return max(int(self.quantity or 0) - int(self.printed_quantity or 0), 0)

    @property
    def print_progress_percent(self) -> int:
        qty = int(self.quantity or 0)
        if qty <= 0:
            return 0
        return min(int((int(self.printed_quantity or 0) / qty) * 100), 100)

    @property
    def can_mark_ready(self) -> bool:
        return (
            self.status == self.Status.PENDING
            and int(self.printed_quantity or 0) >= int(self.quantity or 0)
            and bool(self.bound_done)
            and not bool(self.spine_unavailable)
        )

    def mark_ready(self):
        if not self.can_mark_ready:
            return False
        self.status = self.Status.READY
        self.completed_at = timezone.now()
        self.print_done = True
        self.bound_done = True
        self.save(update_fields=["status", "completed_at", "print_done", "bound_done", "updated_at"])
        return True


class SheetClassMapping(models.Model):
    tutoring_class = models.ForeignKey(
        TutoringClass,
        verbose_name="Class",
        on_delete=models.CASCADE,
        related_name="sheet_mappings",
    )
    sheet = models.ForeignKey(
        Sheet,
        verbose_name="ชีท",
        on_delete=models.CASCADE,
        related_name="class_mappings",
    )
    quantity_per_student = models.PositiveIntegerField(
        "จำนวนชีทต่อเด็ก 1 คน",
        default=1,
        help_text="ใช้คำนวณว่ารายการสมัคร/ทดลองเรียนต้องใช้ชีทกี่ชุด",
    )
    is_active = models.BooleanField("ใช้งาน", default=True)
    note = models.CharField("หมายเหตุ", max_length=255, blank=True)
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Sheet Class Mapping"
        verbose_name_plural = "Sheet Class Mappings"
        ordering = ("tutoring_class__time_slot", "tutoring_class__name", "sheet__code")
        constraints = [
            models.UniqueConstraint(
                fields=["tutoring_class", "sheet"],
                name="uniq_sheet_mapping_per_class",
            )
        ]

    def __str__(self) -> str:
        return f"{self.tutoring_class} | {self.sheet.code}"




class SheetAllocation(models.Model):
    class RecipientType(models.TextChoices):
        STUDENT = "student", "Student ในระบบ"
        ADMISSION = "admission", "สมัครเรียน/ทดลองเรียน"
        MANUAL = "manual", "กรอกเอง"
        UNASSIGNED = "unassigned", "ไม่ระบุชื่อ"

    sheet = models.ForeignKey(
        Sheet,
        verbose_name="ชีท",
        on_delete=models.PROTECT,
        related_name="allocations",
    )
    quantity = models.PositiveIntegerField("จำนวนที่แจก", default=1)
    allocation_date = models.DateField("วันที่แจก", default=timezone.localdate)

    recipient_type = models.CharField(
        "ประเภทผู้รับ",
        max_length=20,
        choices=RecipientType.choices,
        default=RecipientType.UNASSIGNED,
    )
    student = models.ForeignKey(
        Student,
        verbose_name="นักเรียนในระบบ",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sheet_allocations",
    )
    admission_inquiry = models.ForeignKey(
        "AdmissionInquiry",
        verbose_name="รายการสมัคร/ทดลองเรียน",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sheet_allocations",
    )
    manual_nickname = models.CharField("ชื่อเล่นที่กรอกเอง", max_length=100, blank=True)
    manual_grade_level = models.CharField("ระดับชั้นที่กรอกเอง", max_length=50, blank=True)
    tutoring_class = models.ForeignKey(
        TutoringClass,
        verbose_name="Class ที่เกี่ยวข้อง",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sheet_allocations",
    )
    scan_code = models.CharField("รหัสที่สแกน", max_length=80, blank=True)
    batch_key = models.CharField("Batch", max_length=40, blank=True)
    note = models.CharField("หมายเหตุ", max_length=255, blank=True)
    movement = models.ForeignKey(
        SheetInventoryMovement,
        verbose_name="Movement ที่ตัด stock",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allocations",
    )
    created_by = models.ForeignKey(
        "auth.User",
        verbose_name="ผู้บันทึก",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sheet_allocations",
    )
    created_at = models.DateTimeField("วันที่บันทึก", default=timezone.now)

    class Meta:
        verbose_name = "Sheet Allocation"
        verbose_name_plural = "Sheet Allocations"
        ordering = ("-allocation_date", "-created_at", "sheet__code")
        indexes = [
            models.Index(fields=["allocation_date", "recipient_type"]),
            models.Index(fields=["sheet", "allocation_date"]),
            models.Index(fields=["student", "allocation_date"]),
            models.Index(fields=["tutoring_class", "allocation_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.allocation_date} | {self.sheet.code} | {self.recipient_display}"

    @property
    def recipient_display(self) -> str:
        if self.student_id:
            return self.student.display_name
        if self.admission_inquiry_id:
            return f"{self.admission_inquiry.nickname} | {self.admission_inquiry.full_name}"
        if self.manual_nickname:
            return f"{self.manual_nickname} {self.manual_grade_level}".strip()
        return "ไม่ระบุชื่อ"


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
    target_class = models.ForeignKey(
        TutoringClass,
        verbose_name="Class ที่คาดว่าจะเข้าเรียน",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_inquiries",
        help_text="ใช้สำหรับประมาณที่นั่งว่างและติดตามเด็กสมัคร/ทดลองเรียน",
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

    attended_first_lesson = models.BooleanField(
        "มาเรียนแล้ว (รอสร้างใบเสร็จ)",
        default=False,
        help_text="ติ๊กจากปุ่ม “มาแล้ว” ในภาพรวมเรียลไทม์ของ Admin Tool -- การ์ดยังอยู่ต่อจนกว่าจะสร้างใบเสร็จ",
    )

    is_completed = models.BooleanField("ดำเนินการเสร็จแล้ว", default=False)
    completed_at = models.DateTimeField("วันที่ดำเนินการเสร็จ", null=True, blank=True)

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


class NewStudentPaymentNotice(models.Model):
    """
    ใบแจ้งชำระค่าคอร์สสำหรับนักเรียนใหม่ที่ยังไม่มี Student/Enrollment จริงในระบบ --
    สร้างจากข้อมูลที่กรอกไว้ใน AdmissionInquiry (ระบบรับสมัคร) เก็บเป็น snapshot
    แก้ไขได้อิสระโดยไม่กระทบข้อมูลต้นทาง แยกจาก CourseRenewalNotice เพราะยังไม่มี
    Enrollment ให้ผูก และไม่มีแนวคิด "ใกล้ครบคอร์ส"/เครดิตชวนเพื่อนแบบนักเรียนเดิม
    """

    admission_inquiry = models.ForeignKey(
        AdmissionInquiry,
        verbose_name="ใบสมัครอ้างอิง",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_student_payment_notices",
        help_text="ใบสมัครที่ใช้ดึงข้อมูลมาตอนสร้าง (ไม่ผูกติดกัน แก้ไขในใบแจ้งนี้ได้อิสระ)",
    )

    nickname = models.CharField("ชื่อเล่น", max_length=100, blank=True)
    first_name = models.CharField("ชื่อจริง", max_length=150, blank=True)
    last_name = models.CharField("นามสกุล", max_length=150, blank=True)
    school_name = models.CharField("โรงเรียน", max_length=255, blank=True)
    contact_phone = models.CharField("เบอร์ติดต่อ", max_length=50, blank=True)
    grade_level = models.CharField(
        "ระดับชั้น",
        max_length=20,
        choices=AdmissionInquiry.GradeLevel.choices,
        blank=True,
    )
    target_class = models.ForeignKey(
        TutoringClass,
        verbose_name="Class ที่คาดว่าจะเข้าเรียน",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_student_payment_notices",
    )
    first_lesson_date = models.DateField("วันที่เริ่มเรียนวันแรก", null=True, blank=True)

    class PricingOption(models.TextChoices):
        TRIAL_THEN_ENROLL = "trial_then_enroll", "ทดลองเรียนแล้วสมัคร"
        NO_TRIAL = "no_trial", "สมัครโดยไม่ทดลอง"

    pricing_option = models.CharField(
        "รูปแบบการสมัคร",
        max_length=20,
        choices=PricingOption.choices,
        default=PricingOption.TRIAL_THEN_ENROLL,
    )

    # Base ("สมัครโดยไม่ทดลอง") package discounts; "ทดลองเรียนแล้วสมัคร" tops
    # each one up by an extra 190 baht, since that parent already paid for a
    # trial lesson that now counts toward enrolling.
    BASE_PACKAGE_DISCOUNTS = {10: Decimal("0"), 20: Decimal("300"), 30: Decimal("800")}
    TRIAL_TOPUP_DISCOUNT = Decimal("190")

    @classmethod
    def default_discounts_for(cls, pricing_option: str) -> dict[int, Decimal]:
        extra = cls.TRIAL_TOPUP_DISCOUNT if pricing_option == cls.PricingOption.TRIAL_THEN_ENROLL else Decimal("0")
        return {n: base + extra for n, base in cls.BASE_PACKAGE_DISCOUNTS.items()}

    package_10_full_price = models.DecimalField("10 สัปดาห์ - ราคาเต็ม", max_digits=10, decimal_places=2, default=3990)
    package_10_discount = models.DecimalField("10 สัปดาห์ - ส่วนลด", max_digits=10, decimal_places=2, default=0)
    package_10_net_price = models.DecimalField("10 สัปดาห์ - ราคาสุทธิ", max_digits=10, decimal_places=2, default=3990)

    package_20_full_price = models.DecimalField("20 สัปดาห์ - ราคาเต็ม", max_digits=10, decimal_places=2, default=7980)
    package_20_discount = models.DecimalField("20 สัปดาห์ - ส่วนลด", max_digits=10, decimal_places=2, default=300)
    package_20_net_price = models.DecimalField("20 สัปดาห์ - ราคาสุทธิ", max_digits=10, decimal_places=2, default=7680)

    package_30_full_price = models.DecimalField("30 สัปดาห์ - ราคาเต็ม", max_digits=10, decimal_places=2, default=11970)
    package_30_discount = models.DecimalField("30 สัปดาห์ - ส่วนลด", max_digits=10, decimal_places=2, default=800)
    package_30_net_price = models.DecimalField("30 สัปดาห์ - ราคาสุทธิ", max_digits=10, decimal_places=2, default=11170)

    note_wording = models.TextField(
        "ข้อความท้ายใบแจ้ง",
        default="ชำระแล้วรบกวนส่งสลิปแจ้งพี่ขนุนทาง Line @ เพื่อยืนยันที่นั่งและออกใบเสร็จให้ครับ",
    )

    is_sent_to_parent = models.BooleanField("ส่งแจ้งผู้ปกครองแล้ว", default=False)
    sent_to_parent_at = models.DateTimeField("วันที่ส่งแจ้งผู้ปกครอง", null=True, blank=True)
    sent_to_parent_by = models.ForeignKey(
        "auth.User",
        verbose_name="ผู้กดส่งแจ้ง",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_new_student_payment_notices",
    )

    created_by = models.ForeignKey(
        "auth.User",
        verbose_name="ผู้สร้าง",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_new_student_payment_notices",
    )
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "New Student Payment Notice"
        verbose_name_plural = "New Student Payment Notices"
        ordering = ("-created_at",)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return f"ใบแจ้งชำระนักเรียนใหม่ | {self.nickname or self.full_name} | {self.created_at:%d/%m/%Y}"

    def save(self, *args, **kwargs):
        self.package_10_net_price = max((self.package_10_full_price or 0) - (self.package_10_discount or 0), Decimal("0"))
        self.package_20_net_price = max((self.package_20_full_price or 0) - (self.package_20_discount or 0), Decimal("0"))
        self.package_30_net_price = max((self.package_30_full_price or 0) - (self.package_30_discount or 0), Decimal("0"))
        super().save(*args, **kwargs)


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
    default_special_rate_325 = models.BooleanField(
        "ค่าเริ่มต้นเรทพิเศษ 325 บาท/ชม.",
        default=False,
        help_text="ถ้าติ๊ก ช่องเรทพิเศษ 325 จะถูกติ๊กให้อัตโนมัติเมื่อกรอกค่าสอนของติวเตอร์คนนี้",
    )
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
    teaching_hours = models.DecimalField("จำนวนชั่วโมงสอน onsite", max_digits=5, decimal_places=2, default=0)
    special_rate_325 = models.BooleanField(
        "ใช้อัตราพิเศษ 325 บาท/ชม. เมื่อสอนตั้งแต่ 4 ชม.",
        default=False,
        help_text="ติ๊กเฉพาะติวเตอร์ที่ได้เรทพิเศษ กรณีสอน onsite ตั้งแต่ 4 ชั่วโมงขึ้นไป",
    )
    hourly_rate = models.DecimalField("เรท onsite ต่อชั่วโมง", max_digits=10, decimal_places=2, default=0)
    hourly_rate_override = models.DecimalField(
        "เรทค่าสอนที่กำหนดเอง", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="เว้นว่างเพื่อใช้เรทเริ่มต้นตามชั่วโมงสอน/เรทพิเศษ 325 โดยอัตโนมัติ ใส่ตัวเลขเพื่อ override",
    )
    teaching_fee = models.DecimalField("ค่าสอน onsite", max_digits=12, decimal_places=2, default=0)
    online_teaching_hours = models.DecimalField("จำนวนชั่วโมงสอนออนไลน์", max_digits=5, decimal_places=2, default=0)
    online_teaching_fee = models.DecimalField("ค่าสอนออนไลน์", max_digits=12, decimal_places=2, default=0)
    travel_fee = models.DecimalField("ค่าเดินทาง", max_digits=12, decimal_places=2, default=0)
    travel_fee_override = models.DecimalField(
        "ค่าเดินทางที่กำหนดเอง", max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="เว้นว่างเพื่อใช้ค่าเดินทางเริ่มต้นตามชั่วโมงสอนโดยอัตโนมัติ ใส่ตัวเลขเพื่อ override",
    )
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
    def calculate_hourly_rate(hours: Decimal, special_rate_325: bool = False) -> Decimal:
        hours = Decimal(str(hours or 0))
        if hours <= 0:
            return Decimal("0")
        if hours <= 1:
            return Decimal("550")
        if hours < 4:
            return Decimal("350")
        return Decimal("325") if special_rate_325 else Decimal("300")

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

    @staticmethod
    def calculate_online_teaching_fee(online_hours: Decimal) -> Decimal:
        online_hours = Decimal(str(online_hours or 0))
        if online_hours <= 0:
            return Decimal("0")
        return online_hours * Decimal("300")

    def recalculate(self):
        hours = Decimal(str(self.teaching_hours or 0))
        online_hours = Decimal(str(self.online_teaching_hours or 0))

        # hourly_rate/travel_fee stay auto-calculated by default; an explicit
        # override (set from the schedule payroll popup or elsewhere) wins.
        self.hourly_rate = (
            Decimal(str(self.hourly_rate_override))
            if self.hourly_rate_override is not None
            else self.calculate_hourly_rate(hours, self.special_rate_325)
        )
        self.teaching_fee = hours * self.hourly_rate
        self.online_teaching_hours = online_hours
        self.online_teaching_fee = self.calculate_online_teaching_fee(online_hours)
        self.travel_fee = (
            Decimal(str(self.travel_fee_override))
            if self.travel_fee_override is not None
            else self.calculate_travel_fee(hours)
        )
        self.idle_fee = Decimal(str(self.idle_fee or 0))
        self.total_amount = self.teaching_fee + self.online_teaching_fee + self.travel_fee + self.idle_fee

    def save(self, *args, **kwargs):
        self.recalculate()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.work_date} | {self.tutor} | {self.total_amount:,.2f}"

# =========================================================
# Tutor Teaching Update Module (Independent from old ClassSubject)
# =========================================================
class TeachingTutor(models.Model):
    DEFAULT_SHEET_PIN = "123456"

    name = models.CharField("ชื่อติวเตอร์", max_length=120, unique=True)
    sheet_pin_hash = models.CharField(
        "รหัส PIN ระบบชีท (เข้ารหัส)",
        max_length=255,
        blank=True,
        help_text="ว่าง = ยังไม่เคยตั้ง PIN ระบบจะใช้ค่าเริ่มต้น 123456",
    )
    phone = models.CharField("เบอร์ติดต่อ", max_length=50, blank=True)
    color = models.CharField("สีประจำตัว (ใช้บนตารางเรียน)", max_length=20, default="#1d4ed8")
    payroll_tutor = models.ForeignKey(
        "Tutor", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="teaching_profiles",
        verbose_name="ผูกกับติวเตอร์ในระบบเงิน (รายจ่าย/ค่าสอน)",
    )
    note = models.TextField("หมายเหตุ", blank=True)
    is_active = models.BooleanField("ใช้งาน", default=True)
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Teaching Tutor"
        verbose_name_plural = "Teaching Tutors"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def check_sheet_pin(self, raw: str) -> bool:
        """PINs are hashed. A tutor who has never set one keeps the shared
        default, so the reader is usable the day it ships."""
        from django.contrib.auth.hashers import check_password
        raw = (raw or "").strip()
        if not self.sheet_pin_hash:
            return raw == self.DEFAULT_SHEET_PIN
        return check_password(raw, self.sheet_pin_hash)

    def set_sheet_pin(self, raw: str) -> None:
        from django.contrib.auth.hashers import make_password
        self.sheet_pin_hash = make_password((raw or "").strip())

    @property
    def sheet_pin_is_default(self) -> bool:
        return not self.sheet_pin_hash


class TutorSheetProgress(models.Model):
    """Where a class got to in a given sheet.

    Keyed by class rather than tutor: two classes work through the same
    sheet at their own pace, and whoever teaches next should pick up where
    that class stopped, not where that tutor stopped.
    """

    tutoring_class = models.ForeignKey(
        TutoringClass,
        verbose_name="คลาส",
        on_delete=models.CASCADE,
        related_name="tutor_sheet_progress",
    )
    sheet = models.ForeignKey(
        Sheet,
        verbose_name="ชีท",
        on_delete=models.CASCADE,
        related_name="tutor_progress",
    )
    document = models.ForeignKey(
        "SheetDocument",
        verbose_name="ไฟล์ที่เปิดค้างไว้",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tutor_progress",
    )
    last_page = models.PositiveIntegerField("หน้าล่าสุด", default=1)
    last_question = models.CharField("ข้อล่าสุด", max_length=50, blank=True)
    updated_by_name = models.CharField("ผู้บันทึกล่าสุด", max_length=120, blank=True)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)

    class Meta:
        verbose_name = "Tutor Sheet Progress"
        verbose_name_plural = "Tutor Sheet Progress"
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["tutoring_class", "sheet"],
                name="uniq_tutor_sheet_progress_per_class_sheet",
            )
        ]

    def __str__(self) -> str:
        return f"{self.tutoring_class} | {self.sheet.code} | หน้า {self.last_page}"


class TutorSheetMarkup(models.Model):
    """Highlighter markup a tutor drew on one page of one PDF file.

    Keyed by tutor + document + page (NOT by class, unlike TutorSheetProgress)
    -- the pen marks belong to that tutor's own copy of the book, so they
    follow the tutor across whichever class they open the sheet from.
    Never rendered back into the PDF; `strokes` is just vector paths (points
    normalized 0-1 against the page's un-zoomed size) redrawn on an overlay
    canvas client-side.
    """

    tutor = models.ForeignKey(
        TeachingTutor,
        verbose_name="ติวเตอร์",
        on_delete=models.CASCADE,
        related_name="sheet_markups",
    )
    document = models.ForeignKey(
        "SheetDocument",
        verbose_name="เล่ม (ไฟล์ PDF)",
        on_delete=models.CASCADE,
        related_name="tutor_markups",
    )
    page = models.PositiveIntegerField("หน้าที่")
    strokes = models.JSONField("ขีดเขียน", default=list, blank=True)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)

    class Meta:
        verbose_name = "Tutor Sheet Markup"
        verbose_name_plural = "Tutor Sheet Markups"
        ordering = ("document", "page")
        constraints = [
            models.UniqueConstraint(
                fields=["tutor", "document", "page"],
                name="uniq_tutor_sheet_markup_per_tutor_document_page",
            )
        ]

    def __str__(self) -> str:
        return f"{self.tutor.name} | {self.document} | หน้า {self.page}"


class TeachingClassSubjectTemplate(models.Model):
    tutoring_class = models.ForeignKey(
        TutoringClass,
        verbose_name="คลาส",
        on_delete=models.CASCADE,
        related_name="teaching_subject_templates",
    )
    subject_name = models.CharField("ชื่อวิชา", max_length=120)
    default_sheet_name = models.CharField(
        "ชื่อชีท/เอกสารตั้งต้น",
        max_length=255,
        blank=True,
        help_text="ใช้ prefill ให้ติวเตอร์ในแต่ละสัปดาห์",
    )
    default_sheet = models.ForeignKey(
        Sheet,
        verbose_name="ชีทในระบบ (ใช้คิด % ความคืบหน้า)",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_subject_templates",
        help_text=(
            "ปกติระบบจับคู่ชีทให้อัตโนมัติจากรหัสชีทที่ติวเตอร์กรอก "
            "ตั้งค่านี้เมื่ออยากบังคับให้ใช้ชีทเล่มนี้คิด % แทนการจับคู่อัตโนมัติ"
        ),
    )
    display_order = models.PositiveIntegerField("ลำดับแสดงผล", default=1)
    is_active = models.BooleanField("ใช้งาน", default=True)
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Teaching Subject Template"
        verbose_name_plural = "Teaching Subject Templates"
        ordering = ("tutoring_class__name", "display_order", "subject_name")
        constraints = [
            models.UniqueConstraint(
                fields=["tutoring_class", "subject_name"],
                name="uniq_teaching_subject_per_class",
            )
        ]

    def __str__(self) -> str:
        return f"{self.tutoring_class} | {self.subject_name}"


class TeachingWeeklyAssignment(models.Model):
    week_start_date = models.DateField("วันเริ่มสัปดาห์เรียน", help_text="ระบบใช้วันเสาร์เป็นต้นสัปดาห์")
    week_end_date = models.DateField("วันสิ้นสุดสัปดาห์เรียน", help_text="ระบบใช้วันอาทิตย์เป็นวันสิ้นสุด")
    tutoring_class = models.ForeignKey(
        TutoringClass,
        verbose_name="คลาส",
        on_delete=models.CASCADE,
        related_name="teaching_weekly_assignments",
    )
    subject_template = models.ForeignKey(
        TeachingClassSubjectTemplate,
        verbose_name="วิชาใน template",
        on_delete=models.CASCADE,
        related_name="weekly_assignments",
    )
    tutor = models.ForeignKey(
        TeachingTutor,
        verbose_name="ติวเตอร์",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_assignments",
    )
    is_teaching = models.BooleanField(
        "สัปดาห์นี้มีสอน",
        default=True,
        help_text="ใช้ปิดรายการที่สัปดาห์นี้ไม่มีสอน โดยยังเก็บ assignment ไว้ในระบบ",
    )
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Teaching Weekly Assignment"
        verbose_name_plural = "Teaching Weekly Assignments"
        ordering = ("week_start_date", "tutoring_class__name", "subject_template__display_order")
        constraints = [
            models.UniqueConstraint(
                fields=["week_start_date", "subject_template"],
                name="uniq_teaching_assignment_per_week_subject",
            )
        ]

    def __str__(self) -> str:
        tutor_name = self.tutor.name if self.tutor_id else "ยังไม่ระบุ"
        return f"{self.week_start_date} | {self.tutoring_class} | {self.subject_template.subject_name} | {tutor_name}"


class TeachingProgressUpdate(models.Model):
    assignment = models.ForeignKey(
        TeachingWeeklyAssignment,
        verbose_name="Assignment",
        on_delete=models.CASCADE,
        related_name="progress_updates",
    )
    teaching_date = models.DateField("วันที่สอน", default=timezone.localdate)
    sheet_name = models.CharField("ชื่อชีท/เอกสาร", max_length=255, blank=True)
    page_to = models.CharField("สอนถึงหน้า", max_length=50, blank=True)
    question_to = models.CharField("สอนถึงข้อ", max_length=50, blank=True)
    no_teaching = models.BooleanField("สัปดาห์นี้ไม่มีสอน", default=False)
    sheet_near_end = models.BooleanField(
        "ใกล้จบชีท",
        default=False,
        help_text="ติ๊กเมื่อชีทใกล้จบ เพื่อให้แสดงกรอบเตือนสีแดงในหน้าติวเตอร์",
    )
    updated_by_name = models.CharField("ผู้บันทึก", max_length=120, blank=True)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)
    created_at = models.DateTimeField("วันที่สร้าง", default=timezone.now)

    class Meta:
        verbose_name = "Teaching Progress Update"
        verbose_name_plural = "Teaching Progress Updates"
        ordering = ("-teaching_date", "-updated_at")
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "teaching_date"],
                name="uniq_teaching_progress_per_assignment_date",
            )
        ]

    def __str__(self) -> str:
        return f"{self.assignment} | {self.teaching_date}"

    @property
    def progress_text(self) -> str:
        parts = []
        if self.sheet_name:
            parts.append(self.sheet_name)
        if self.page_to:
            parts.append(f"หน้า {self.page_to}")
        if self.question_to:
            parts.append(f"ข้อ {self.question_to}")
        text = " / ".join(parts) if parts else "-"
        if self.no_teaching:
            return f"สัปดาห์นี้ไม่มีสอน · ข้อมูลล่าสุด: {text}"
        if self.sheet_near_end:
            return f"{text} · ใกล้จบชีท"
        return text

# =========================================================
# ✅ Test Score Announcement Module
# =========================================================


# -----------------------
# Weekly Small Test (Test ย่อยรายสัปดาห์)
# -----------------------
class WeeklyTest(models.Model):
    """รอบ Test ย่อยรายสัปดาห์ ผูกกับสัปดาห์แบบ Sat-Sun ของ Dashboard"""

    DIFFICULTY_CHOICES = [(i, "⭐" * i) for i in range(1, 6)]

    week_start = models.DateField(
        "สัปดาห์ที่เริ่มวันเสาร์",
        help_text="ระบบใช้สัปดาห์เดียวกับ Dashboard: เสาร์-อาทิตย์",
    )
    grade_level = models.CharField(
        "ระดับชั้น",
        max_length=20,
        choices=Sheet.GradeLevel.choices,
        default=Sheet.GradeLevel.P4,
        help_text="แยกหัวข้อ Test เป็นรายระดับชั้น เช่น ป.4 / ป.5 / ม.1",
    )
    test_date = models.DateField("วันที่แสดงบนใบประกาศ", default=timezone.localdate)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_tests",
        verbose_name="วิชาในระบบ",
    )
    subject_name = models.CharField(
        "วิชา / ชื่อวิชาแบบกรอกเอง",
        max_length=120,
        blank=True,
        help_text="ใช้กรณีอยากกรอกชื่อวิชาเอง หรือไม่มีใน Subject",
    )
    topic = models.CharField("เรื่อง", max_length=255, blank=True)
    difficulty = models.PositiveSmallIntegerField("ระดับความยาก", choices=DIFFICULTY_CHOICES, default=3)
    note = models.TextField("หมายเหตุ", blank=True)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_tests_created",
    )
    updated_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_tests_updated",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Weekly Small Test"
        verbose_name_plural = "Weekly Small Tests"
        constraints = [
            models.UniqueConstraint(fields=["week_start", "grade_level"], name="uniq_weekly_test_per_week_grade")
        ]
        ordering = ("-week_start", "grade_level", "-created_at")

    def __str__(self) -> str:
        return f"Test ย่อย {self.week_start} [{self.grade_display}] - {self.subject_display}"

    @property
    def grade_display(self) -> str:
        try:
            return self.get_grade_level_display()
        except Exception:
            return self.grade_level or "-"

    @property
    def subject_display(self) -> str:
        if self.subject_id and self.subject:
            return self.subject.name
        return self.subject_name or "-"

    @property
    def difficulty_stars(self) -> str:
        return "⭐" * int(self.difficulty or 0)


class WeeklyTestScore(models.Model):
    class Result(models.TextChoices):
        FAIL = "fail", "ไม่ผ่าน"
        MEDIUM = "medium", "ปานกลาง"
        GOOD = "good", "ดี"
        GREAT = "great", "ดีมาก"
        FULL = "full", "เต็ม"

    class AttendanceStatus(models.TextChoices):
        PRESENT = Attendance.Status.PRESENT, "มา"
        EXCUSED = Attendance.Status.EXCUSED, "ลา"
        NO_SHOW = Attendance.Status.NO_SHOW, "ขาด"
        NOT_CHECKED = "not_checked", "ยังไม่เช็คชื่อ"

    weekly_test = models.ForeignKey(WeeklyTest, on_delete=models.CASCADE, related_name="scores")
    enrollment = models.ForeignKey(Enrollment, on_delete=models.PROTECT, related_name="weekly_test_scores")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="weekly_test_scores")
    tutoring_class = models.ForeignKey(TutoringClass, on_delete=models.PROTECT, related_name="weekly_test_scores")
    attendance_date = models.DateField("วันที่อ้างอิงจาก Dashboard", null=True, blank=True)
    attendance_status = models.CharField(
        "สถานะจาก Dashboard",
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.NOT_CHECKED,
    )
    result = models.CharField("ผล Test", max_length=20, choices=Result.choices, blank=True, default="")
    note = models.CharField("หมายเหตุ", max_length=255, blank=True)
    updated_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Weekly Small Test Score"
        verbose_name_plural = "Weekly Small Test Scores"
        constraints = [
            models.UniqueConstraint(fields=["weekly_test", "enrollment"], name="uniq_weekly_test_score_per_enrollment")
        ]
        ordering = ("weekly_test", "tutoring_class__name", "student__nickname", "student__full_name")

    def __str__(self) -> str:
        return f"{self.weekly_test} | {self.student} | {self.get_result_display() if self.result else self.get_attendance_status_display()}"


class TestRound(models.Model):
    title = models.CharField("ชื่อรอบสอบ", max_length=255)
    exam_date = models.DateField("วันที่สอบ", null=True, blank=True)
    is_published = models.BooleanField("เปิดให้ผู้ปกครองดู", default=False)
    note = models.TextField("หมายเหตุ", blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Test Round"
        verbose_name_plural = "Test Rounds"
        ordering = ("-exam_date", "-created_at")

    def __str__(self) -> str:
        return self.title


class TestSubject(models.Model):
    test_round = models.ForeignKey(TestRound, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField("ชื่อวิชา", max_length=120)
    full_score = models.DecimalField("คะแนนเต็ม", max_digits=8, decimal_places=2, default=100)
    display_order = models.PositiveIntegerField("ลำดับ", default=1)
    is_active = models.BooleanField("ใช้งาน", default=True)
    note = models.CharField("หมายเหตุ", max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Test Subject"
        verbose_name_plural = "Test Subjects"
        ordering = ("test_round", "display_order", "id")

    def __str__(self) -> str:
        return f"{self.test_round} - {self.name}"


class TestParticipant(models.Model):
    class SourceType(models.TextChoices):
        STUDENT = "student", "นักเรียนในระบบ"
        ADMISSION = "admission", "จากระบบรับสมัคร"
        MANUAL = "manual", "กรอกเอง"

    test_round = models.ForeignKey(TestRound, on_delete=models.CASCADE, related_name="participants")
    source_type = models.CharField("แหล่งข้อมูล", max_length=20, choices=SourceType.choices, default=SourceType.MANUAL)
    student = models.ForeignKey("Student", on_delete=models.SET_NULL, null=True, blank=True, related_name="test_participations")
    admission_inquiry = models.ForeignKey("AdmissionInquiry", on_delete=models.SET_NULL, null=True, blank=True, related_name="test_participations")

    nickname = models.CharField("ชื่อเล่น", max_length=100, blank=True)
    full_name = models.CharField("ชื่อจริงนามสกุล", max_length=255)
    school_name = models.CharField("โรงเรียน", max_length=255, blank=True)
    contact_phone = models.CharField("เบอร์ติดต่อ", max_length=50, blank=True)
    grade_level = models.CharField("ระดับชั้น", max_length=50, blank=True)
    note = models.TextField("หมายเหตุ", blank=True)
    is_active = models.BooleanField("ใช้งาน", default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Test Participant"
        verbose_name_plural = "Test Participants"
        ordering = ("test_round", "full_name", "nickname")

    def __str__(self) -> str:
        return f"{self.nickname or '-'} | {self.full_name}"

    @property
    def display_name(self) -> str:
        if self.nickname:
            return f"{self.nickname} - {self.full_name}"
        return self.full_name


class TestScore(models.Model):
    participant = models.ForeignKey(TestParticipant, on_delete=models.CASCADE, related_name="scores")
    subject = models.ForeignKey(TestSubject, on_delete=models.CASCADE, related_name="scores")
    score = models.DecimalField("คะแนนที่ได้", max_digits=8, decimal_places=2, default=0)
    note = models.CharField("หมายเหตุรายวิชา", max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Test Score"
        verbose_name_plural = "Test Scores"
        constraints = [
            models.UniqueConstraint(fields=["participant", "subject"], name="uniq_test_score_per_subject")
        ]
        ordering = ("participant", "subject__display_order", "subject_id")

    def __str__(self) -> str:
        return f"{self.participant} - {self.subject.name}: {self.score}"


class AdminToolCard(models.Model):
    """A configurable menu card shown on the Pkanoon Admin Tool landing page.

    Stored in DB so every admin/device sees the same shared configuration.
    """

    class Section(models.TextChoices):
        PRIVATE = "private", "Private / Management"
        OPERATION = "operation", "Operation"

    section = models.CharField("หมวด", max_length=20, choices=Section.choices, default=Section.PRIVATE)
    icon = models.CharField("ไอคอน", max_length=16, default="🔗")
    name = models.CharField("ชื่อเมนู", max_length=200)
    desc = models.TextField("คำอธิบาย", blank=True)
    url = models.CharField("ลิงก์", max_length=300)
    quick_add_url = models.CharField(
        "ลิงก์ปุ่ม + (ลัดไปหน้าสร้างใหม่)",
        max_length=300,
        blank=True,
        help_text="ถ้าใส่ จะมีปุ่ม + ที่มุมขวาบนของ card เพื่อลัดไปหน้าสร้างรายการใหม่",
    )
    color = models.CharField("สีไอคอน", max_length=20, default="c-sky")
    order = models.IntegerField("ลำดับ", default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Admin Tool Card"
        verbose_name_plural = "Admin Tool Cards"
        ordering = ("section", "order", "id")

    def __str__(self) -> str:
        return f"[{self.section}] {self.name}"

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "section": self.section,
            "icon": self.icon,
            "name": self.name,
            "desc": self.desc,
            "url": self.url,
            "quick_add_url": self.quick_add_url,
            "color": self.color,
            "order": self.order,
        }



# =========================================================
# Teaching schedule (weekly class timetable image generator)
# =========================================================
class ScheduleRoom(models.Model):
    """A physical room shown as a column on the schedule (named after fruits).

    A room hosts one class per half-day, and the classes differ between
    Saturday and Sunday. These bindings are standing defaults (they rarely
    change, so they automatically apply to every following week). They drive
    the subject/tutor/grade options in the editor; the class name itself is
    never shown on the generated image.
    """
    name = models.CharField("ชื่อห้อง", max_length=120)
    icon = models.CharField("ไอคอนผลไม้ (emoji)", max_length=16, blank=True, default="")
    header_color = models.CharField("สีหัวคอลัมน์", max_length=20, default="#fdf3bf")
    display_order = models.PositiveIntegerField("ลำดับคอลัมน์", default=1)
    sat_morning_class = models.ForeignKey(
        "TutoringClass", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sat_morning_schedule_rooms", verbose_name="เสาร์เช้า (08.30-12.30)",
    )
    sat_afternoon_class = models.ForeignKey(
        "TutoringClass", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sat_afternoon_schedule_rooms", verbose_name="เสาร์บ่าย (13.30-17.30)",
    )
    sun_morning_class = models.ForeignKey(
        "TutoringClass", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sun_morning_schedule_rooms", verbose_name="อาทิตย์เช้า (08.30-12.30)",
    )
    sun_afternoon_class = models.ForeignKey(
        "TutoringClass", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sun_afternoon_schedule_rooms", verbose_name="อาทิตย์บ่าย (13.30-17.30)",
    )
    is_active = models.BooleanField("ใช้งาน", default=True)

    class Meta:
        verbose_name = "Schedule Room"
        verbose_name_plural = "Schedule Rooms"
        ordering = ("display_order", "id")

    def __str__(self) -> str:
        return self.name

    def class_for(self, is_sunday: bool, is_afternoon: bool):
        if is_sunday:
            return self.sun_afternoon_class if is_afternoon else self.sun_morning_class
        return self.sat_afternoon_class if is_afternoon else self.sat_morning_class


class ScheduleExamCountdown(models.Model):
    """An exam date shown as a countdown badge in the schedule footer."""
    grade_label = models.CharField("ระดับชั้น", max_length=40)  # e.g. "ม.1"
    exam_date = models.DateField("วันสอบ")
    note = models.CharField("หมายเหตุ (เช่น รอบแรก - ห้องพิเศษ)", max_length=120, blank=True)
    display_order = models.PositiveIntegerField("ลำดับ", default=1)
    is_active = models.BooleanField("แสดงบนตาราง", default=True)
    show_on_saturday = models.BooleanField("แสดงในตารางวันเสาร์", default=True)
    show_on_sunday = models.BooleanField("แสดงในตารางวันอาทิตย์", default=True)

    class Meta:
        verbose_name = "Schedule Exam Countdown"
        verbose_name_plural = "Schedule Exam Countdowns"
        ordering = ("display_order", "exam_date", "id")

    def __str__(self) -> str:
        return f"{self.grade_label} - {self.exam_date}"


class DailySchedule(models.Model):
    """One day's timetable. The rendered image shows the Thai date derived from it."""
    date = models.DateField("วันที่", unique=True)
    title_note = models.CharField("ข้อความหัวเรื่องเพิ่มเติม", max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Daily Schedule"
        verbose_name_plural = "Daily Schedules"
        ordering = ("-date",)

    def __str__(self) -> str:
        return f"ตารางเรียน {self.date.isoformat()}"


class DailyScheduleCell(models.Model):
    """A single cell (room x time slot) inside a DailySchedule."""
    schedule = models.ForeignKey(DailySchedule, on_delete=models.CASCADE, related_name="cells")
    room = models.ForeignKey(ScheduleRoom, on_delete=models.CASCADE, related_name="cells")
    time_index = models.PositiveIntegerField("ลำดับคาบ")  # index into TEACHING_SCHEDULE_SLOTS

    tutoring_class = models.ForeignKey(
        "TutoringClass", on_delete=models.SET_NULL, null=True, blank=True, related_name="schedule_cells",
    )
    subject_template = models.ForeignKey(
        "TeachingClassSubjectTemplate", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="schedule_cells",
    )
    tutor = models.ForeignKey(
        "TeachingTutor", on_delete=models.SET_NULL, null=True, blank=True, related_name="schedule_cells",
    )
    # Snapshot / override text shown on the image
    grade_label = models.CharField("ระดับชั้น", max_length=40, blank=True)
    subject_label = models.CharField("วิชา", max_length=120, blank=True)

    class Meta:
        verbose_name = "Daily Schedule Cell"
        verbose_name_plural = "Daily Schedule Cells"
        ordering = ("time_index", "room__display_order")
        constraints = [
            models.UniqueConstraint(fields=["schedule", "room", "time_index"], name="uniq_schedule_cell"),
        ]

    def __str__(self) -> str:
        return f"{self.schedule_id} r{self.room_id} t{self.time_index}"

    @property
    def is_empty(self) -> bool:
        return not (self.grade_label or self.subject_label or self.tutor_id)


# =========================================================
# Online course video clips (embedded playback for parents/students)
# =========================================================
class OnlineCourseVideo(models.Model):
    """A recorded lesson clip stored in Google Drive, embedded for playback
    directly on the Online Course page instead of linking out to Drive."""
    course_key = models.CharField(
        "รหัสคอร์ส", max_length=50, default="p6",
        help_text="ใช้แยกชุดคลิปตามคอร์ส เช่น p6",
    )
    title = models.CharField("ชื่อคลิป", max_length=255)
    drive_url = models.URLField(
        "ลิงก์ Google Drive",
        max_length=1000,
        help_text="วางลิงก์แชร์ไฟล์วิดีโอจาก Google Drive (ต้องแชร์แบบ 'ทุกคนที่มีลิงก์ดูได้')",
    )
    note = models.CharField("หมายเหตุ (เช่น สัปดาห์ที่สอน)", max_length=255, blank=True)
    subject_tag = models.CharField("วิชา", max_length=100, blank=True)
    tutor_name = models.CharField("ชื่อติวเตอร์", max_length=120, blank=True)
    duration_minutes = models.PositiveIntegerField(
        "ความยาวคลิป (นาที)", default=0,
        help_text="ใช้สำหรับ auto play คลิปถัดไปเมื่อคลิปนี้จบ (0 = ไม่ทราบ ระบบจะไม่ auto ต่อ)",
    )
    display_order = models.PositiveIntegerField("ลำดับแสดงผล", default=1)
    is_active = models.BooleanField("แสดงให้ดู", default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Online Course Video"
        verbose_name_plural = "Online Course Videos"
        ordering = ("course_key", "display_order", "-created_at")

    def __str__(self) -> str:
        return f"[{self.course_key}] {self.title}"

    @property
    def drive_file_id(self) -> str:
        m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", self.drive_url or "")
        if m:
            return m.group(1)
        m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", self.drive_url or "")
        return m.group(1) if m else ""

    @property
    def embed_url(self) -> str:
        file_id = self.drive_file_id
        return f"https://drive.google.com/file/d/{file_id}/preview" if file_id else ""

    @property
    def thumbnail_url(self) -> str:
        file_id = self.drive_file_id
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w480" if file_id else ""


# =========================================================
# Star Quiz system (weekly quizzes -> stars -> prize redemption)
# =========================================================
class StarQuiz(models.Model):
    """A weekly quiz shown to students of one grade level. Accumulating
    stars from completed quizzes lets students redeem prizes (redemption
    itself is tracked/handled outside the system, offline)."""

    grade_level = models.CharField(
        "ระดับชั้น", max_length=20, choices=Sheet.GradeLevel.choices,
        help_text="แสดงเทสนี้ให้เฉพาะนักเรียนระดับชั้นนี้เห็น",
    )
    code = models.CharField(
        "รหัสเทส", max_length=40, unique=True, blank=True,
        help_text="ระบบสร้างให้อัตโนมัติ เช่น ป.6 Test 001",
    )
    title = models.CharField("ชื่อเทส / หัวข้อ", max_length=255)
    subject_tag = models.CharField("วิชา", max_length=100, blank=True)
    star_reward = models.PositiveIntegerField(
        "ดาวเต็มของเทสนี้", default=5,
        help_text="ดาวที่ได้จะคำนวณตามสัดส่วนคะแนนที่ทำได้ เช่น ได้ 80% ของคะแนน = ได้ 80% ของดาวเต็ม (ปัดเศษ)",
    )
    publish_at = models.DateTimeField(
        "วันเผยแพร่", default=timezone.now,
        help_text="เทสจะเปิดให้ทำตั้งแต่วันเวลานี้เป็นต้นไป (ตั้งล่วงหน้าได้)",
    )
    expires_at = models.DateTimeField(
        "วันหมดอายุ", null=True, blank=True,
        help_text="เว้นว่างได้ถ้าไม่ต้องการวันหมดอายุ",
    )
    is_active = models.BooleanField("เปิดใช้งาน", default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Star Quiz"
        verbose_name_plural = "Star Quizzes"
        ordering = ("-publish_at", "-id")

    def __str__(self) -> str:
        return self.code or self.title

    def save(self, *args, **kwargs):
        if not self.code and self.grade_level:
            grade_label = dict(Sheet.GradeLevel.choices).get(self.grade_level, self.grade_level)
            seq = StarQuiz.objects.filter(grade_level=self.grade_level).count() + 1
            candidate = f"{grade_label} Test {seq:03d}"
            while StarQuiz.objects.filter(code=candidate).exists():
                seq += 1
                candidate = f"{grade_label} Test {seq:03d}"
            self.code = candidate
        super().save(*args, **kwargs)

    @property
    def is_published(self) -> bool:
        now = timezone.now()
        if self.publish_at and self.publish_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < timezone.now())

    @property
    def total_points(self) -> int:
        return sum(q.points for q in self.questions.all())

    @property
    def has_written_questions(self) -> bool:
        return self.questions.filter(question_type=StarQuizQuestion.QuestionType.WRITTEN).exists()


class StarQuizQuestion(models.Model):
    class QuestionType(models.TextChoices):
        MCQ = "mcq", "ข้อกา (ปรนัย)"
        WRITTEN = "written", "ข้อเขียน (อัตนัย)"

    quiz = models.ForeignKey(StarQuiz, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField("ลำดับข้อ", default=1)
    question_type = models.CharField(
        "ประเภทข้อ", max_length=20, choices=QuestionType.choices, default=QuestionType.MCQ,
    )
    question_text = models.TextField("โจทย์")
    points = models.PositiveIntegerField("คะแนนของข้อนี้", default=1)
    correct_choice_index = models.PositiveIntegerField(
        "เฉลย (ลำดับช้อยส์ที่ถูก เริ่มที่ 0)", null=True, blank=True,
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Star Quiz Question"
        verbose_name_plural = "Star Quiz Questions"
        ordering = ("quiz", "order", "id")

    def __str__(self) -> str:
        return f"{self.quiz.code} #{self.order}"


class StarQuizChoice(models.Model):
    question = models.ForeignKey(StarQuizQuestion, on_delete=models.CASCADE, related_name="choices")
    order = models.PositiveIntegerField("ลำดับช้อยส์", default=1)
    text = models.CharField("ข้อความช้อยส์", max_length=500, blank=True)

    class Meta:
        verbose_name = "Star Quiz Choice"
        verbose_name_plural = "Star Quiz Choices"
        ordering = ("question", "order", "id")

    def __str__(self) -> str:
        return f"{self.question_id} - {self.text[:30]}"


class StarQuizAttempt(models.Model):
    quiz = models.ForeignKey(StarQuiz, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="star_quiz_attempts")
    submitted_at = models.DateTimeField(default=timezone.now)
    score_points = models.PositiveIntegerField("คะแนนที่ได้", default=0)
    max_points = models.PositiveIntegerField("คะแนนเต็ม", default=0)
    stars_awarded = models.PositiveIntegerField("ดาวที่ได้", default=0)
    is_graded = models.BooleanField(
        "ตรวจครบแล้ว", default=False,
        help_text="เป็น False ถ้ามีข้อเขียนที่ยังไม่ได้ตรวจ ดาวจะยังไม่ตัดให้จนกว่าจะตรวจครบ",
    )

    class Meta:
        verbose_name = "Star Quiz Attempt"
        verbose_name_plural = "Star Quiz Attempts"
        ordering = ("-submitted_at",)
        constraints = [
            models.UniqueConstraint(fields=["quiz", "student"], name="uniq_star_quiz_attempt_per_student"),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.quiz.code}"

    def recalculate(self):
        answers = list(self.answers.select_related("question"))
        score = sum(a.points_awarded for a in answers)
        pending = any(
            a.question.question_type == StarQuizQuestion.QuestionType.WRITTEN and a.points_awarded is None
            for a in answers
        )
        self.score_points = score
        self.is_graded = not pending
        if self.is_graded and self.max_points:
            self.stars_awarded = round(self.quiz.star_reward * (self.score_points / self.max_points))
        elif self.is_graded:
            self.stars_awarded = 0
        self.save(update_fields=["score_points", "stars_awarded", "is_graded"])


class StarQuizAnswer(models.Model):
    attempt = models.ForeignKey(StarQuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(StarQuizQuestion, on_delete=models.CASCADE, related_name="answers")
    selected_choice = models.ForeignKey(
        StarQuizChoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    written_answer = models.TextField("คำตอบข้อเขียน", blank=True)
    points_awarded = models.PositiveIntegerField("คะแนนที่ได้ข้อนี้", null=True, blank=True)

    class Meta:
        verbose_name = "Star Quiz Answer"
        verbose_name_plural = "Star Quiz Answers"
        ordering = ("attempt", "question__order")
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="uniq_star_quiz_answer_per_question"),
        ]

    def __str__(self) -> str:
        return f"{self.attempt_id} - Q{self.question_id}"


# =========================================================
# Revenue & Cost Analysis (วิเคราะห์รายได้ ต้นทุน กำไร รายห้อง)
# =========================================================
class CostScenario(models.Model):
    """A saved what-if model for one month.

    Every number here is an *assumption* the user can override. Actuals are
    pulled from Attendance/Enrollment/SchoolExpense only to pre-fill the form,
    so a scenario stays reproducible even after the underlying data changes.
    """

    class Allocation(models.TextChoices):
        STUDENTS = "students", "ตามจำนวนนักเรียน (แนะนำ)"
        HOURS = "hours", "ตามชั่วโมงสอน"
        REVENUE = "revenue", "ตามสัดส่วนรายได้"
        EQUAL = "equal", "หารเท่ากันทุกห้อง"

    name = models.CharField("ชื่อ Scenario", max_length=150)
    period_month = models.DateField(
        "เดือนที่วิเคราะห์",
        help_text="ใช้แค่เดือน/ปี (วันที่จะถูกปรับเป็นวันที่ 1 อัตโนมัติ)",
    )
    allocation_method = models.CharField(
        "วิธีปันส่วน Fixed Cost",
        max_length=20,
        choices=Allocation.choices,
        default=Allocation.STUDENTS,
    )
    default_teaching_cost_per_hour = models.DecimalField(
        "ค่าสอนต่อชั่วโมง (ค่าเริ่มต้น)", max_digits=10, decimal_places=2, default=Decimal("300")
    )
    default_revenue_per_student_hour = models.DecimalField(
        "รายได้ต่อคนต่อชั่วโมง (ค่าเริ่มต้น)", max_digits=10, decimal_places=2, default=Decimal("150")
    )
    default_hours_per_session = models.DecimalField(
        "ชั่วโมงต่อครั้ง (ค่าเริ่มต้น)", max_digits=5, decimal_places=2, default=Decimal("4")
    )
    default_sessions_per_month = models.DecimalField(
        "จำนวนครั้งต่อเดือน (ค่าเริ่มต้น)", max_digits=5, decimal_places=2, default=Decimal("4"),
        help_text="ปกติ 1 สัปดาห์เรียน 1 ครั้ง",
    )
    note = models.TextField("บันทึก", blank=True)
    created_at = models.DateTimeField("สร้างเมื่อ", default=timezone.now)
    updated_at = models.DateTimeField("อัปเดตล่าสุด", auto_now=True)

    class Meta:
        verbose_name = "Cost Scenario"
        verbose_name_plural = "Cost Scenarios"
        ordering = ("-period_month", "-updated_at")

    def save(self, *args, **kwargs):
        if self.period_month:
            self.period_month = self.period_month.replace(day=1)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.period_month:%m/%Y})"

    @property
    def total_fixed_cost(self) -> Decimal:
        return sum((f.amount for f in self.fixed_costs.all()), Decimal("0"))


class CostScenarioFixedCost(models.Model):
    """One monthly fixed-cost line item (rent, staff salary, utilities, ...)."""

    scenario = models.ForeignKey(
        CostScenario, on_delete=models.CASCADE, related_name="fixed_costs", verbose_name="Scenario"
    )
    name = models.CharField("รายการ", max_length=150)
    amount = models.DecimalField("จำนวนเงินต่อเดือน", max_digits=12, decimal_places=2, default=0)
    note = models.CharField("หมายเหตุ", max_length=255, blank=True)
    order = models.IntegerField("ลำดับ", default=0)

    class Meta:
        verbose_name = "Cost Scenario Fixed Cost"
        verbose_name_plural = "Cost Scenario Fixed Costs"
        ordering = ("order", "id")

    def __str__(self) -> str:
        return f"{self.name} = {self.amount:,.2f}"


class CostScenarioClass(models.Model):
    """Per-class inputs. Blank override fields fall back to the scenario default."""

    scenario = models.ForeignKey(
        CostScenario, on_delete=models.CASCADE, related_name="class_inputs", verbose_name="Scenario"
    )
    tutoring_class = models.ForeignKey(
        TutoringClass, on_delete=models.CASCADE, related_name="cost_inputs", verbose_name="Class"
    )
    is_included = models.BooleanField("รวมในการวิเคราะห์", default=True)

    student_count = models.PositiveIntegerField("จำนวนนักเรียน", default=0)
    sessions_per_month = models.DecimalField(
        "จำนวนครั้งในเดือนนี้", max_digits=5, decimal_places=2, null=True, blank=True
    )
    hours_per_session = models.DecimalField(
        "ชั่วโมงต่อครั้ง", max_digits=5, decimal_places=2, null=True, blank=True
    )
    teaching_cost_per_hour = models.DecimalField(
        "ค่าสอนต่อชั่วโมง", max_digits=10, decimal_places=2, null=True, blank=True
    )
    revenue_per_student_hour = models.DecimalField(
        "รายได้ต่อคนต่อชั่วโมง", max_digits=10, decimal_places=2, null=True, blank=True
    )
    other_variable_cost = models.DecimalField(
        "ต้นทุนผันแปรอื่นต่อเดือน", max_digits=12, decimal_places=2, default=0,
        help_text="เช่น ค่าชีท ค่าขนม เฉพาะห้องนี้",
    )

    class Meta:
        verbose_name = "Cost Scenario Class Input"
        verbose_name_plural = "Cost Scenario Class Inputs"
        ordering = ("tutoring_class__name",)
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "tutoring_class"], name="uniq_cost_scenario_class"
            )
        ]

    def __str__(self) -> str:
        return f"{self.scenario_id} - {self.tutoring_class_id}"
