from django.db import models, transaction
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

    student_code = models.CharField(
        "รหัสนักเรียน", max_length=5, unique=True, blank=True,
        help_text="ระบบสร้างอัตโนมัติรูปแบบ YY### เช่น 25001",
    )
    full_name = models.CharField("ชื่อจริงนามสกุล", max_length=255)
    nickname = models.CharField("ชื่อเล่น", max_length=100, blank=True)
    profile_image = models.ImageField("รูปประจำตัว", upload_to="student_profiles/", blank=True, null=True)
    grade_level = models.CharField("ระดับชั้น", max_length=50, blank=True)
    academic_year = models.CharField("ปีการศึกษา", max_length=20, blank=True)
    school = models.ForeignKey(
        School, verbose_name="โรงเรียน", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="students",
    )
    parent_phone = models.CharField("เบอร์ผู้ปกครอง", max_length=50)
    contact_channel = models.CharField(
        "ช่องทางติดต่อ", max_length=20,
        choices=ContactChannel.choices, default=ContactChannel.LINE,
    )
    enroll_date = models.DateField("วันที่สมัคร", default=timezone.localdate)
    referral_source = models.CharField(
        "ช่องทางที่รู้จัก", max_length=20,
        choices=ReferralSource.choices, default=ReferralSource.REFERRAL,
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
        parts = filter(None, [
            self.student_code, self.nickname, self.full_name,
            self.grade_level, self.school.name if self.school else None,
        ])
        return " | ".join(parts)

    @staticmethod
    def _next_student_code_for_year(two_digit_year: str) -> str:
        last = (
            Student.objects.filter(student_code__startswith=two_digit_year)
            .order_by("-student_code").values_list("student_code", flat=True).first()
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
# TutoringClass
# -----------------------
class TutoringClass(models.Model):
    class TimeSlot(models.TextChoices):
        SAT_MORNING = "sat_morning", "เสาร์เช้า"
        SAT_AFTERNOON = "sat_afternoon", "เสาร์บ่าย"
        SUN_MORNING = "sun_morning", "อาทิตย์เช้า"
        SUN_AFTERNOON = "sun_afternoon", "อาทิตย์บ่าย"

    name = models.CharField("ชื่อคลาส", max_length=100, unique=True)
    course_price = models.DecimalField("ราคาคอร์ส (เต็ม)", max_digits=10, decimal_places=2, default=0)
    total_seats = models.PositiveIntegerField("ที่นั่งรวม", default=0)
    time_slot = models.CharField(
        "รอบเวลา", max_length=20, choices=TimeSlot.choices, default=TimeSlot.SAT_MORNING,
    )
    hours_per_session = models.DecimalField("ชั่วโมงต่อครั้ง", max_digits=4, decimal_places=2, default=3.00)
    is_active = models.BooleanField("เปิดใช้งาน", default=True)

    class Meta:
        verbose_name = "Class"
        verbose_name_plural = "Classes"

    def __str__(self) -> str:
        return self.name


# -----------------------
# Subject
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
# Sheet
# -----------------------
class Sheet(models.Model):
    code = models.CharField("รหัสชีท", max_length=50, unique=True)
    title = models.CharField("เรื่อง", max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="sheets")
    total_pages = models.PositiveIntegerField("จำนวนหน้า", default=0)
    total_questions = models.PositiveIntegerField("จำนวนข้อ", default=0)
    is_active = models.BooleanField("เปิดใช้งาน", default=True)

    class Meta:
        verbose_name = "Sheet"
        verbose_name_plural = "Sheets"
        ordering = ("subject__name", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.title}"


# -----------------------
# ClassSubject
# -----------------------
class ClassSubject(models.Model):
    tutoring_class = models.ForeignKey(TutoringClass, on_delete=models.CASCADE, related_name="class_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="class_subjects")
    current_sheet = models.ForeignKey(
        Sheet, on_delete=models.SET_NULL, null=True, blank=True, related_name="active_class_subjects",
    )
    current_page = models.PositiveIntegerField("หน้าที่สอนถึง", default=0)
    current_question = models.PositiveIntegerField("ข้อที่สอนถึง", default=0)
    last_teacher = models.CharField("สอนโดย", max_length=100, blank=True)
    is_active = models.BooleanField("เปิดใช้งาน", default=True)
    updated_at = models.DateTimeField(default=timezone.now)
    updated_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Class Subject"
        verbose_name_plural = "Class Subjects"
        unique_together = ("tutoring_class", "subject")

    def __str__(self) -> str:
        return f"{self.tutoring_class} — {self.subject}"


# -----------------------
# Enrollment
# -----------------------
class Enrollment(models.Model):
    class PaymentType(models.TextChoices):
        FULL = "full", "ชำระเต็ม"
        INSTALLMENT = "installment", "ผ่อนชำระ"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="enrollments")
    tutoring_class = models.ForeignKey(TutoringClass, on_delete=models.PROTECT, related_name="enrollments")
    sale_run_no = models.CharField("เลขที่ใบขาย", max_length=20, blank=True, unique=True, null=True)
    sessions_total = models.IntegerField("จำนวนครั้งทั้งหมด", default=0)
    remark = models.TextField("หมายเหตุ", blank=True)
    is_active = models.BooleanField("คอร์สยังอยู่", default=True)
    created_at = models.DateTimeField(default=timezone.now)
    payment_type = models.CharField(
        "ประเภทชำระ", max_length=20, choices=PaymentType.choices, default=PaymentType.FULL,
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
        if is_new and not self.sale_run_no:
            student_code = (self.student.student_code or "").strip() if self.student_id else ""
            if student_code:
                with transaction.atomic():
                    last = (
                        Enrollment.objects.select_for_update()
                        .filter(student_id=self.student_id, sale_run_no__startswith=f"{student_code}-")
                        .order_by("-sale_run_no").values_list("sale_run_no", flat=True).first()
                    )
                    seq = int(str(last).split("-")[-1]) + 1 if last else 1
                    self.sale_run_no = f"{student_code}-{seq:02d}"
        if self.sessions_total is None:
            self.sessions_total = 0
        if self.sessions_total <= 0:
            auto_note = "ครบคอร์สแล้ว (นำเข้าข้อมูลย้อนหลัง)"
            note = (self.remark or "").strip()
            if auto_note not in note:
                self.remark = f"{note}\n{auto_note}".strip()
        if self.tutoring_class_id and not self.course_price:
            self.course_price = self.tutoring_class.course_price or 0
        if self.payment_type == self.PaymentType.FULL:
            self.installments_count = 1
        elif not self.installments_count or self.installments_count < 1:
            self.installments_count = 1
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
# EnrollmentInstallment
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
# Attendance
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
        if self.quantity is None:
            self.quantity = 0
        if self.quantity < 0:
            self.quantity = 0
        if self.is_finished and not self.finished_at:
            self.finished_at = timezone.now()
        if not self.is_finished:
            self.finished_at = None
        super().save(*args, **kwargs)


# =============================================================
# QUIZ MODELS — standalone ไม่ขึ้นกับตารางอื่นใดเลย
# ทุก field ที่ผู้ใช้กรอก = CharField ธรรมดา (free text)
# =============================================================

GRADE_CHOICES = [
    ("ป.1", "ป.1"), ("ป.2", "ป.2"), ("ป.3", "ป.3"),
    ("ป.4", "ป.4"), ("ป.5", "ป.5"), ("ป.6", "ป.6"),
    ("ม.1", "ม.1"), ("ม.2", "ม.2"), ("ม.3", "ม.3"),
    ("ม.4", "ม.4"), ("ม.5", "ม.5"), ("ม.6", "ม.6"),
]

SUBJECT_DISPLAY_ORDER = ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"]


class Quiz(models.Model):
    """ชุดข้อสอบ — admin สร้าง ระบุวิชาและระดับชั้นเป็น text ธรรมดา"""
    # วิชาและชั้นเป็น text ธรรมดา ไม่ FK
    subject_name = models.CharField("วิชา", max_length=100, default="คณิตศาสตร์")
    grade_level = models.CharField("ระดับชั้น", max_length=10, choices=GRADE_CHOICES, default="ป.4")
    title = models.CharField("ชื่อชุดข้อสอบ", max_length=255)
    description = models.TextField("คำอธิบาย", blank=True)
    time_limit_minutes = models.PositiveIntegerField("เวลาทำ (นาที, 0=ไม่จำกัด)", default=0)
    pass_score = models.PositiveIntegerField("คะแนนผ่าน (%)", default=60)
    is_active = models.BooleanField("เปิดให้ทำข้อสอบ", default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"
        ordering = ("grade_level", "subject_name", "-created_at")

    def __str__(self) -> str:
        return f"[{self.grade_level}] {self.subject_name} – {self.title}"

    def total_questions(self):
        return self.questions.count()

    def total_score(self):
        from django.db.models import Sum
        return self.questions.aggregate(total=Sum("score"))["total"] or 0


class Question(models.Model):
    class QuestionType(models.TextChoices):
        SINGLE = "single", "เลือกตอบ (1 คำตอบ)"
        MULTI = "multi", "เลือกตอบ (หลายคำตอบ)"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField("ลำดับ", default=1)
    question_type = models.CharField(
        "ประเภท", max_length=20, choices=QuestionType.choices, default=QuestionType.SINGLE,
    )
    text = models.TextField("คำถาม")
    image = models.ImageField("รูปประกอบ", upload_to="quiz_questions/", blank=True, null=True)
    score = models.PositiveIntegerField("คะแนน", default=1)
    explanation = models.TextField("เฉลยอธิบาย", blank=True)

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ("quiz", "order")

    def __str__(self) -> str:
        return f"Q{self.order}: {self.text[:60]}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    label = models.CharField("ตัวอักษร (A/B/C/D)", max_length=10, blank=True)
    text = models.CharField("ข้อความตัวเลือก", max_length=500)
    image = models.ImageField("รูปตัวเลือก", upload_to="quiz_choices/", blank=True, null=True)
    is_correct = models.BooleanField("เป็นคำตอบที่ถูก", default=False)
    order = models.PositiveIntegerField("ลำดับ", default=1)

    class Meta:
        verbose_name = "Choice"
        verbose_name_plural = "Choices"
        ordering = ("question", "order")

    def __str__(self) -> str:
        return f"{self.label}: {self.text[:40]}"


class QuizAttempt(models.Model):
    """ผลการสอบ — ทุก field ของผู้ทำเป็น CharField ธรรมดา ไม่มี FK ใดๆ"""
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "กำลังทำ"
        SUBMITTED = "submitted", "ส่งแล้ว"
        TIMED_OUT = "timed_out", "หมดเวลา"

    # ข้อมูลผู้ทำ — free text ทั้งหมด ไม่ FK
    taker_nickname = models.CharField("ชื่อเล่น", max_length=100)
    taker_firstname = models.CharField("ชื่อจริง", max_length=150)
    taker_lastname = models.CharField("นามสกุล", max_length=150)
    taker_school = models.CharField("โรงเรียน", max_length=255, blank=True)
    taker_grade = models.CharField("ระดับชั้น", max_length=10)
    taker_email = models.EmailField("อีเมล", blank=True)

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField("สถานะ", max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField("เริ่มทำ", default=timezone.now)
    submitted_at = models.DateTimeField("เวลาส่ง", null=True, blank=True)

    score = models.DecimalField("คะแนนที่ได้", max_digits=6, decimal_places=2, default=0)
    max_score = models.DecimalField("คะแนนเต็ม", max_digits=6, decimal_places=2, default=0)
    passed = models.BooleanField("ผ่าน", default=False)

    # ใช้จับกลุ่ม attempt หลาย quiz ในครั้งเดียวกัน
    session_key = models.CharField("Session Key", max_length=64, blank=True, db_index=True)

    class Meta:
        verbose_name = "Quiz Attempt"
        verbose_name_plural = "Quiz Attempts"
        ordering = ("-started_at",)

    def __str__(self) -> str:
        return f"{self.taker_nickname} | {self.quiz} | {self.status}"

    @property
    def taker_full_name(self):
        return f"{self.taker_firstname} {self.taker_lastname}".strip()

    @property
    def score_percent(self):
        if self.max_score:
            return round(float(self.score) / float(self.max_score) * 100, 1)
        return 0

    def calculate_and_save(self):
        total_score = 0
        max_score = 0
        for question in self.quiz.questions.prefetch_related("choices"):
            correct_ids = set(question.choices.filter(is_correct=True).values_list("id", flat=True))
            answered_ids = set(self.answers.filter(question=question).values_list("choice_id", flat=True))
            max_score += question.score
            if answered_ids == correct_ids:
                total_score += question.score
        self.score = total_score
        self.max_score = max_score
        self.passed = (
            (float(total_score) / float(max_score) * 100) >= self.quiz.pass_score
            if max_score > 0 else False
        )
        self.status = QuizAttempt.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.save()


class QuizAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name="answers")

    class Meta:
        verbose_name = "Quiz Answer"
        verbose_name_plural = "Quiz Answers"
        unique_together = ("attempt", "question", "choice")
