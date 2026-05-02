from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils import timezone

from .models import (
    Student,
    School,
    TutoringClass,
    Subject,
    Sheet,
    ClassSubject,
    Enrollment,
    Attendance,
    EnrollmentInstallment,
    SheetInventory,
    Quiz,
    Question,
    Choice,
    QuizAttempt,
    QuizAnswer,
)


# -----------------------
# School
# -----------------------
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    ordering = ("name",)


# -----------------------
# Student
# -----------------------
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    autocomplete_fields = ["school"]

    list_display = (
        "student_code",
        "nickname",
        "full_name",
        "grade_level",
        "school_display",
        "profile_image_thumb",
        "parent_phone",
        "is_active",
    )

    search_fields = (
        "student_code",
        "nickname",
        "full_name",
        "school__name",
        "parent_phone",
    )

    list_filter = (
        "grade_level",
        "is_active",
        "contact_channel",
        "referral_source",
    )

    list_per_page = 50

    readonly_fields = (
        "student_code",
        "profile_image_thumb_large",
        "created_at",
    )

    fieldsets = (
        ("รูปโปรไฟล์", {
            "fields": ("profile_image", "profile_image_thumb_large"),
        }),
        ("ข้อมูลนักเรียน", {
            "fields": (
                "student_code",
                "nickname",
                "full_name",
                "grade_level",
                "academic_year",
                "school",
                "parent_phone",
                "is_active",
            ),
        }),
        ("ข้อมูลการติดต่อ", {
            "fields": (
                "contact_channel",
                "referral_source",
                "enroll_date",
            ),
        }),
        ("หมายเหตุ", {
            "fields": ("note",),
        }),
        ("ระบบ", {
            "fields": ("created_at",),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            yy = str(timezone.localdate().year)[-2:]
            try:
                form.base_fields["student_code"].initial = Student._next_student_code_for_year(yy)
            except Exception:
                pass
        return form

    @admin.display(description="โรงเรียน")
    def school_display(self, obj):
        return obj.school.name if obj.school else "-"

    def profile_image_thumb(self, obj):
        if obj.profile_image:
            return mark_safe(
                f'<img src="{obj.profile_image.url}" '
                f'style="width:40px;height:40px;border-radius:999px;'
                f'object-fit:cover;border:1px solid #e5e7eb;" />'
            )
        return "-"

    def profile_image_thumb_large(self, obj):
        if obj.profile_image:
            return mark_safe(
                f'<img src="{obj.profile_image.url}" '
                f'style="width:160px;height:160px;border-radius:18px;'
                f'object-fit:cover;border:1px solid #e5e7eb;" />'
            )
        return "ยังไม่มีรูป"


# -----------------------
# Subject
# -----------------------
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)
    ordering = ("name",)


# -----------------------
# Sheet
# -----------------------
@admin.register(Sheet)
class SheetAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "subject",
        "total_pages",
        "total_questions",
        "is_active",
    )
    search_fields = ("code", "title")
    list_filter = ("subject", "is_active")
    ordering = ("subject__name", "code")
    autocomplete_fields = ("subject",)


# -----------------------
# ClassSubject inline
# -----------------------
class ClassSubjectInline(admin.TabularInline):
    model = ClassSubject
    extra = 0
    autocomplete_fields = ("subject", "current_sheet")
    fields = (
        "subject",
        "current_sheet",
        "current_page",
        "current_question",
        "last_teacher",
        "is_active",
        "updated_at",
        "updated_by",
    )
    readonly_fields = ("updated_at", "updated_by")


# -----------------------
# TutoringClass
# -----------------------
@admin.register(TutoringClass)
class TutoringClassAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "total_seats",
        "course_price",
        "hours_per_session",
        "is_active",
    )
    search_fields = ("name",)
    list_filter = ("is_active",)
    inlines = (ClassSubjectInline,)


# -----------------------
# ClassSubject
# -----------------------
@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = (
        "tutoring_class",
        "subject",
        "current_sheet",
        "current_page",
        "current_question",
        "last_teacher",
        "is_active",
        "updated_at",
    )
    list_filter = ("tutoring_class", "subject", "is_active")
    search_fields = (
        "tutoring_class__name",
        "subject__name",
        "current_sheet__code",
        "current_sheet__title",
    )
    autocomplete_fields = ("tutoring_class", "subject", "current_sheet")
    readonly_fields = ("updated_at", "updated_by")
    ordering = ("tutoring_class__name", "subject__name")


# -----------------------
# Enrollment + Installments
# -----------------------
class EnrollmentInstallmentInline(admin.TabularInline):
    model = EnrollmentInstallment
    extra = 0
    fields = (
        "installment_no",
        "amount_due",
        "amount_paid",
        "is_paid",
        "paid_at",
        "note",
    )
    readonly_fields = ("is_paid", "paid_at")
    ordering = ("installment_no",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    autocomplete_fields = ("student", "tutoring_class")
    inlines = (EnrollmentInstallmentInline,)

    list_display = (
        "sale_run_no",
        "student",
        "tutoring_class",
        "sessions_total",
        "is_active",
        "payment_type",
        "course_price",
        "net_price",
        "created_at",
    )

    list_filter = (
        "tutoring_class",
        "is_active",
        "payment_type",
    )

    search_fields = (
        "sale_run_no",
        "student__student_code",
        "student__full_name",
        "student__nickname",
        "tutoring_class__name",
    )

    readonly_fields = (
        "sale_run_no",
        "created_at",
        "net_price",
    )

    fieldsets = (
        ("ข้อมูลนักเรียน", {
            "fields": (
                "student",
                "tutoring_class",
                "sale_run_no",
                "created_at",
                "is_active",
            )
        }),
        ("จำนวนครั้ง", {
            "fields": (
                "sessions_total",
                "remark",
            )
        }),
        ("การชำระเงิน", {
            "fields": (
                "payment_type",
                "installments_count",
                "course_price",
                "discount_amount",
                "net_price",
            )
        }),
    )


# -----------------------
# Attendance
# -----------------------
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "attendance_date",
        "student",
        "enrollment",
        "status",
        "deducted",
        "checked_at",
    )
    list_filter = ("attendance_date", "status", "deducted")
    search_fields = (
        "student__full_name",
        "enrollment__tutoring_class__name",
    )
    ordering = ("-attendance_date", "-checked_at")
    autocomplete_fields = ("student", "enrollment")


# -----------------------
# Sheet Inventory
# -----------------------
@admin.register(SheetInventory)
class SheetInventoryAdmin(admin.ModelAdmin):
    list_display = (
        "sheet",
        "quantity",
        "is_finished",
        "updated_at",
    )
    list_filter = ("is_finished", "sheet__subject")
    search_fields = ("sheet__code", "sheet__title")
    autocomplete_fields = ("sheet",)
    ordering = ("sheet__code",)
    readonly_fields = ("updated_at",)


# =============================================================
# QUIZ ADMIN
# =============================================================

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ("order", "label", "text", "image", "is_correct")
    ordering = ("order",)


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    fields = ("order", "question_type", "text", "image", "score", "explanation")
    ordering = ("order",)
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subject",
        "grade_level",
        "total_questions",
        "total_score",
        "time_limit_minutes",
        "pass_score",
        "is_active",
        "created_at",
    )
    list_filter = ("grade_level", "subject", "is_active")
    search_fields = ("title", "subject__name")
    autocomplete_fields = ("subject",)
    inlines = (QuestionInline,)
    readonly_fields = ("created_at",)
    fieldsets = (
        ("ข้อมูลชุดข้อสอบ", {
            "fields": ("title", "subject", "grade_level", "description", "is_active", "created_at")
        }),
        ("กฎการสอบ", {
            "fields": ("time_limit_minutes", "pass_score")
        }),
    )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "question_type", "text_short", "score")
    list_filter = ("quiz", "question_type")
    search_fields = ("text", "quiz__title")
    autocomplete_fields = ("quiz",)
    inlines = (ChoiceInline,)
    ordering = ("quiz", "order")

    @admin.display(description="คำถาม")
    def text_short(self, obj):
        return obj.text[:80] + "..." if len(obj.text) > 80 else obj.text


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0
    readonly_fields = ("question", "choice")
    can_delete = False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "taker_nickname",
        "taker_firstname",
        "taker_lastname",
        "taker_grade",
        "quiz",
        "status",
        "score",
        "max_score",
        "score_percent_display",
        "passed",
        "submitted_at",
    )
    list_filter = ("quiz__grade_level", "quiz__subject", "status", "passed")
    search_fields = ("taker_nickname", "taker_firstname", "taker_lastname", "quiz__title")
    readonly_fields = (
        "taker_nickname", "taker_firstname", "taker_lastname",
        "taker_grade", "taker_school", "taker_email",
        "quiz", "status", "score", "max_score", "passed",
        "started_at", "submitted_at", "session_key",
    )
    inlines = (QuizAnswerInline,)
    ordering = ("-submitted_at",)

    @admin.display(description="% คะแนน")
    def score_percent_display(self, obj):
        return f"{obj.score_percent}%"
