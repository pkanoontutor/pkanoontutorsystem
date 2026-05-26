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
    AdmissionInquiry,
    FinanceSetting,
    ExpenseCategory,
    SchoolExpense,
    Tutor,
    TutorPayrollEntry,
    CoursePayment,
    CourseRenewalNotice,
    TeachingTutor,
    TeachingClassSubjectTemplate,
    TeachingWeeklyAssignment,
    TeachingProgressUpdate,
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

# -----------------------
# Admission Inquiry
# -----------------------
@admin.register(AdmissionInquiry)
class AdmissionInquiryAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "request_type",
        "nickname",
        "full_name_display",
        "grade_level",
        "preferred_time_slot",
        "first_lesson_date",
        "contact_phone",
        "sheet_prepared",
        "trial_attended",
        "trial_result",
        "is_completed",
        "completed_at",
    )
    list_filter = (
        "request_type",
        "grade_level",
        "preferred_time_slot",
        "first_lesson_date",
        "sheet_prepared",
        "trial_attended",
        "trial_result",
        "is_completed",
    )
    search_fields = (
        "nickname",
        "first_name",
        "last_name",
        "school_name",
        "contact_phone",
    )
    readonly_fields = ("created_at", "updated_at", "completed_at")
    ordering = ("-created_at",)
    list_per_page = 50

    fieldsets = (
        ("ข้อมูลจากผู้ปกครอง", {
            "fields": (
                "request_type",
                "nickname",
                "first_name",
                "last_name",
                "school_name",
                "contact_phone",
                "latest_gpa",
                "grade_level",
                "preferred_time_slot",
                "first_lesson_date",
            )
        }),
        ("ข้อมูลติดตามภายในโรงเรียน", {
            "fields": (
                "sheet_prepared",
                "trial_attended",
                "trial_result",
                "internal_note",
                "is_completed",
                "completed_at",
            )
        }),
        ("ระบบ", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    @admin.display(description="ชื่อ-นามสกุล")
    def full_name_display(self, obj):
        return obj.full_name

# =========================================================
# School Finance / Overview Modules
# =========================================================
@admin.register(FinanceSetting)
class FinanceSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "description", "updated_at")
    search_fields = ("key", "description")
    readonly_fields = ("updated_at",)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_tutor_payroll", "is_active", "sort_order")
    list_filter = ("is_tutor_payroll", "is_active")
    search_fields = ("name",)
    ordering = ("sort_order", "name")


@admin.register(SchoolExpense)
class SchoolExpenseAdmin(admin.ModelAdmin):
    list_display = ("expense_date", "category", "vendor", "description", "amount", "payment_method", "created_at")
    list_filter = ("category", "payment_method", "expense_date")
    search_fields = ("vendor", "description", "note")
    autocomplete_fields = ("category",)
    date_hierarchy = "expense_date"
    ordering = ("-expense_date", "-created_at")


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "phone", "note")
    ordering = ("name",)


@admin.register(TutorPayrollEntry)
class TutorPayrollEntryAdmin(admin.ModelAdmin):
    list_display = (
        "work_date",
        "tutor",
        "teaching_hours",
        "special_rate_325",
        "hourly_rate",
        "teaching_fee",
        "online_teaching_hours",
        "online_teaching_fee",
        "travel_fee",
        "idle_fee",
        "total_amount",
    )
    list_filter = ("work_date", "tutor", "special_rate_325")
    search_fields = ("tutor__name", "note")
    autocomplete_fields = ("tutor",)
    readonly_fields = (
        "hourly_rate",
        "teaching_fee",
        "online_teaching_fee",
        "travel_fee",
        "total_amount",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "work_date"
    ordering = ("-work_date", "tutor__name")



@admin.register(CoursePayment)
class CoursePaymentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_no",
        "payment_date",
        "student",
        "tutoring_class",
        "enrollment",
        "sessions_granted",
        "amount_paid",
        "payment_method",
        "payment_type",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_method", "payment_type", "payment_date", "tutoring_class")
    search_fields = (
        "receipt_no",
        "student__student_code",
        "student__nickname",
        "student__full_name",
        "tutoring_class__name",
        "note",
    )
    autocomplete_fields = ("student", "tutoring_class", "enrollment", "created_by", "cancelled_by")
    readonly_fields = (
        "receipt_no",
        "net_amount",
        "created_at",
        "updated_at",
        "cancelled_at",
    )
    date_hierarchy = "payment_date"
    ordering = ("-payment_date", "-created_at")

    fieldsets = (
        ("ข้อมูลใบเสร็จ", {
            "fields": (
                "receipt_no",
                "payment_date",
                "status",
                "student",
                "tutoring_class",
                "enrollment",
                "enrollment_action",
                "enrollment_created",
                "enrollment_sessions_before",
            )
        }),
        ("ข้อมูลคอร์สและยอดเงิน", {
            "fields": (
                "session_package",
                "sessions_granted",
                "course_price",
                "discount_amount",
                "net_amount",
                "amount_paid",
                "payment_type",
                "payment_method",
                "note",
            )
        }),
        ("ระบบ / การยกเลิก", {
            "fields": (
                "created_by",
                "created_at",
                "updated_at",
                "cancelled_at",
                "cancelled_by",
                "cancel_reason",
            )
        }),
    )

# =========================================================
# Tutor Teaching Update Module
# =========================================================
@admin.register(TeachingTutor)
class TeachingTutorAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "is_active", "updated_at")
    search_fields = ("name", "phone")
    list_filter = ("is_active",)
    ordering = ("name",)


@admin.register(TeachingClassSubjectTemplate)
class TeachingClassSubjectTemplateAdmin(admin.ModelAdmin):
    list_display = ("tutoring_class", "subject_name", "default_sheet_name", "display_order", "is_active")
    list_filter = ("tutoring_class", "is_active")
    search_fields = ("tutoring_class__name", "subject_name", "default_sheet_name")
    autocomplete_fields = ("tutoring_class",)
    ordering = ("tutoring_class__name", "display_order", "subject_name")


@admin.register(TeachingWeeklyAssignment)
class TeachingWeeklyAssignmentAdmin(admin.ModelAdmin):
    list_display = ("week_start_date", "week_end_date", "tutoring_class", "subject_display", "tutor", "updated_at")
    list_filter = ("week_start_date", "tutoring_class", "tutor")
    search_fields = ("tutoring_class__name", "subject_template__subject_name", "tutor__name")
    autocomplete_fields = ("tutoring_class", "subject_template", "tutor")
    ordering = ("-week_start_date", "tutoring_class__name", "subject_template__display_order")

    @admin.display(description="วิชา")
    def subject_display(self, obj):
        return obj.subject_template.subject_name if obj.subject_template_id else "-"


@admin.register(TeachingProgressUpdate)
class TeachingProgressUpdateAdmin(admin.ModelAdmin):
    list_display = ("teaching_date", "status_display", "class_display", "subject_display", "tutor_display", "sheet_name", "page_to", "question_to", "updated_by_name", "updated_at")
    list_filter = ("no_teaching", "teaching_date", "assignment__tutoring_class", "assignment__tutor")
    search_fields = (
        "assignment__tutoring_class__name",
        "assignment__subject_template__subject_name",
        "assignment__tutor__name",
        "sheet_name",
        "updated_by_name",
    )
    autocomplete_fields = ("assignment",)
    ordering = ("-teaching_date", "-updated_at")

    @admin.display(description="สถานะ")
    def status_display(self, obj):
        return "ไม่มีสอน" if getattr(obj, "no_teaching", False) else "บันทึกการสอน"

    @admin.display(description="คลาส")
    def class_display(self, obj):
        return obj.assignment.tutoring_class.name if obj.assignment_id else "-"

    @admin.display(description="วิชา")
    def subject_display(self, obj):
        return obj.assignment.subject_template.subject_name if obj.assignment_id else "-"

    @admin.display(description="ติวเตอร์")
    def tutor_display(self, obj):
        return obj.assignment.tutor.name if obj.assignment_id and obj.assignment.tutor_id else "-"




# -----------------------
# Course Renewal Notice
# -----------------------
@admin.register(CourseRenewalNotice)
class CourseRenewalNoticeAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "student",
        "tutoring_class",
        "enrollment",
        "expected_course_end_date",
        "next_course_start_date",
        "package_10_net_price",
        "package_20_net_price",
        "package_30_net_price",
    )
    list_filter = (
        "expected_course_end_date",
        "next_course_start_date",
        "tutoring_class",
        "created_at",
    )
    search_fields = (
        "student__student_code",
        "student__nickname",
        "student__full_name",
        "tutoring_class__name",
        "enrollment__sale_run_no",
    )
    autocomplete_fields = ("student", "tutoring_class", "enrollment", "created_by")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

