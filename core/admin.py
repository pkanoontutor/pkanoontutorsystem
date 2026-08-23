from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils import timezone

from .models import (
    CostScenario,
    CostScenarioClass,
    CostScenarioFixedCost,
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
    SheetInventoryMovement,
    SheetClassMapping,
    SheetPrintOrder,
    SheetAllocation,
    AdmissionInquiry,
    FinanceSetting,
    ExpenseCategory,
    SchoolExpense,
    Tutor,
    TutorPayrollEntry,
    CoursePayment,
    CourseRenewalNotice,
    NewStudentPaymentNotice,
    TeachingTutor,
    ScheduleRoom,
    ScheduleExamCountdown,
    DailySchedule,
    DailyScheduleCell,
    OnlineCourseVideo,
    TeachingClassSubjectTemplate,
    TeachingWeeklyAssignment,
    TeachingProgressUpdate,
    WeeklyTest,
    WeeklyTestScore,
    TestRound,
    TestSubject,
    TestParticipant,
    TestScore,
    AdminToolCard,
    StarQuiz,
    StarQuizQuestion,
    StarQuizChoice,
    StarQuizAttempt,
    StarQuizAnswer,
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
        "grade_level",
        "subject",
        "total_pages",
        "total_questions",
        "is_active",
    )
    search_fields = ("code", "title", "subject__name")
    list_filter = ("grade_level", "subject", "is_active")
    ordering = ("grade_level", "subject__name", "code")
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
        "minimum_stock",
        "stock_status",
        "is_finished",
        "updated_at",
    )
    list_filter = ("is_finished", "sheet__grade_level", "sheet__subject")
    search_fields = ("sheet__code", "sheet__title")
    autocomplete_fields = ("sheet",)
    ordering = ("sheet__code",)
    readonly_fields = ("updated_at",)

    @admin.display(description="สถานะ")
    def stock_status(self, obj):
        minimum = int(getattr(obj, "minimum_stock", 0) or 0)
        qty = int(obj.quantity or 0)
        if minimum > 0 and qty <= minimum:
            return "ใกล้หมด"
        return "ปกติ"


@admin.register(SheetInventoryMovement)
class SheetInventoryMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "sheet",
        "movement_type",
        "quantity",
        "balance_before",
        "balance_after",
        "created_by",
        "note",
    )
    list_filter = ("movement_type", "created_at", "sheet__grade_level", "sheet__subject")
    search_fields = ("sheet__code", "sheet__title", "note")
    autocomplete_fields = ("sheet", "created_by")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(SheetClassMapping)
class SheetClassMappingAdmin(admin.ModelAdmin):
    list_display = (
        "tutoring_class",
        "sheet",
        "quantity_per_student",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active", "tutoring_class", "sheet__grade_level", "sheet__subject")
    search_fields = ("tutoring_class__name", "sheet__code", "sheet__title")
    autocomplete_fields = ("tutoring_class", "sheet")
    ordering = ("tutoring_class__time_slot", "tutoring_class__name", "sheet__code")


@admin.register(SheetPrintOrder)
class SheetPrintOrderAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "item_display",
        "quantity",
        "printed_quantity",
        "print_done",
        "bound_done",
        "spine_unavailable",
        "binding_type",
        "spine_color",
        "due_date",
        "status",
        "requested_by",
        "completed_at",
    )
    list_filter = (
        "status",
        "print_done",
        "bound_done",
        "spine_unavailable",
        "due_date",
        "binding_type",
        "spine_color",
        "sheet__grade_level",
        "sheet__subject",
    )
    search_fields = ("sheet__code", "sheet__title", "custom_title", "note", "onedrive_url")
    autocomplete_fields = ("sheet", "requested_by")
    readonly_fields = ("created_at", "updated_at", "completed_at")
    ordering = ("status", "due_date", "created_at")

    @admin.display(description="รายการ")
    def item_display(self, obj):
        if obj.sheet_id:
            return f"{obj.sheet.code} - {obj.sheet.title}"
        return obj.custom_title or "เอกสารอื่น"



@admin.register(SheetAllocation)
class SheetAllocationAdmin(admin.ModelAdmin):
    list_display = (
        "allocation_date",
        "sheet",
        "quantity",
        "recipient_type",
        "recipient_display_admin",
        "tutoring_class",
        "created_by",
        "created_at",
    )
    list_filter = ("recipient_type", "allocation_date", "sheet__grade_level", "sheet__subject", "tutoring_class")
    search_fields = (
        "sheet__code",
        "sheet__title",
        "student__student_code",
        "student__nickname",
        "student__full_name",
        "admission_inquiry__nickname",
        "manual_nickname",
        "note",
    )
    autocomplete_fields = ("sheet", "student", "admission_inquiry", "tutoring_class", "movement", "created_by")
    readonly_fields = ("created_at",)
    ordering = ("-allocation_date", "-created_at")

    @admin.display(description="ผู้รับ")
    def recipient_display_admin(self, obj):
        return obj.recipient_display


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
        "target_class",
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
        "target_class",
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
    autocomplete_fields = ("target_class",)

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
                "target_class",
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
    list_display = ("name", "phone", "default_special_rate_325", "is_active", "updated_at")
    list_filter = ("is_active", "default_special_rate_325")
    list_editable = ("default_special_rate_325",)
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
    list_display = ("name", "phone", "color", "payroll_tutor", "is_active", "updated_at")
    list_editable = ("color",)
    search_fields = ("name", "phone")
    list_filter = ("is_active",)
    autocomplete_fields = ("payroll_tutor",)
    ordering = ("name",)


@admin.register(TeachingClassSubjectTemplate)
class TeachingClassSubjectTemplateAdmin(admin.ModelAdmin):
    list_display = ("tutoring_class", "subject_name", "default_sheet_name", "default_sheet", "display_order", "is_active")
    list_filter = ("tutoring_class", "is_active")
    search_fields = ("tutoring_class__name", "subject_name", "default_sheet_name")
    autocomplete_fields = ("tutoring_class", "default_sheet")
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
        "notice_type",
        "installment_no",
        "installment_sessions",
        "student",
        "tutoring_class",
        "enrollment",
        "source_payment",
        "expected_course_end_date",
        "next_course_start_date",
        "is_sent_to_parent",
        "sent_to_parent_at",
        "installment_remaining_amount",
    )
    list_filter = (
        "notice_type",
        "installment_no",
        "is_sent_to_parent",
        "sent_to_parent_at",
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
        "source_payment__receipt_no",
    )
    autocomplete_fields = (
        "student",
        "tutoring_class",
        "enrollment",
        "source_payment",
        "created_by",
        "sent_to_parent_by",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "package_10_net_price",
        "package_20_net_price",
        "package_30_net_price",
        "installment_remaining_amount",
    )
    ordering = ("-created_at",)


@admin.register(NewStudentPaymentNotice)
class NewStudentPaymentNoticeAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "nickname",
        "first_name",
        "last_name",
        "school_name",
        "grade_level",
        "target_class",
        "admission_inquiry",
        "is_sent_to_parent",
        "sent_to_parent_at",
    )
    list_filter = ("grade_level", "is_sent_to_parent", "target_class")
    search_fields = (
        "nickname",
        "first_name",
        "last_name",
        "school_name",
        "contact_phone",
        "admission_inquiry__nickname",
    )
    autocomplete_fields = ("admission_inquiry", "target_class", "created_by", "sent_to_parent_by")
    readonly_fields = (
        "created_at",
        "updated_at",
        "package_10_net_price",
        "package_20_net_price",
        "package_30_net_price",
    )
    ordering = ("-created_at",)

# -----------------------
# Test Score Announcement
# -----------------------
class TestSubjectInline(admin.TabularInline):
    model = TestSubject
    extra = 0
    fields = ("display_order", "name", "full_score", "is_active", "note")


class TestScoreInline(admin.TabularInline):
    model = TestScore
    extra = 0
    autocomplete_fields = ("subject",)
    fields = ("subject", "score", "note", "updated_at")
    readonly_fields = ("updated_at",)




# -----------------------
# Weekly Small Test
# -----------------------
class WeeklyTestScoreInline(admin.TabularInline):
    model = WeeklyTestScore
    extra = 0
    autocomplete_fields = ("enrollment", "student", "tutoring_class")
    fields = ("student", "tutoring_class", "attendance_date", "attendance_status", "result", "note", "updated_by", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(WeeklyTest)
class WeeklyTestAdmin(admin.ModelAdmin):
    list_display = ("week_start", "grade_level", "test_date", "subject_display", "topic", "difficulty", "updated_at")
    list_filter = ("week_start", "grade_level", "subject", "difficulty")
    search_fields = ("subject_name", "subject__name", "topic")
    autocomplete_fields = ("subject",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (WeeklyTestScoreInline,)

    @admin.display(description="วิชา")
    def subject_display(self, obj):
        return obj.subject_display


@admin.register(WeeklyTestScore)
class WeeklyTestScoreAdmin(admin.ModelAdmin):
    list_display = ("weekly_test", "student", "tutoring_class", "attendance_status", "result", "updated_at")
    list_filter = ("weekly_test", "tutoring_class", "attendance_status", "result")
    search_fields = (
        "student__student_code",
        "student__nickname",
        "student__full_name",
        "tutoring_class__name",
        "weekly_test__topic",
        "weekly_test__subject_name",
        "weekly_test__subject__name",
    )
    autocomplete_fields = ("weekly_test", "enrollment", "student", "tutoring_class")
    readonly_fields = ("updated_at",)


@admin.register(TestRound)
class TestRoundAdmin(admin.ModelAdmin):
    list_display = ("title", "exam_date", "is_published", "created_at", "updated_at")
    list_filter = ("is_published", "exam_date")
    search_fields = ("title", "note")
    inlines = (TestSubjectInline,)
    ordering = ("-exam_date", "-created_at")


@admin.register(TestSubject)
class TestSubjectAdmin(admin.ModelAdmin):
    list_display = ("test_round", "display_order", "name", "full_score", "is_active")
    list_filter = ("test_round", "is_active")
    search_fields = ("test_round__title", "name")
    ordering = ("test_round", "display_order", "id")


@admin.register(TestParticipant)
class TestParticipantAdmin(admin.ModelAdmin):
    list_display = ("test_round", "nickname", "full_name", "school_name", "source_type", "is_active")
    list_filter = ("test_round", "source_type", "is_active")
    search_fields = ("nickname", "full_name", "school_name", "contact_phone", "student__student_code")
    autocomplete_fields = ("test_round", "student", "admission_inquiry")
    inlines = (TestScoreInline,)
    ordering = ("test_round", "full_name")


@admin.register(TestScore)
class TestScoreAdmin(admin.ModelAdmin):
    list_display = ("participant", "subject", "score", "updated_at")
    list_filter = ("subject__test_round", "subject")
    search_fields = ("participant__nickname", "participant__full_name", "subject__name")
    autocomplete_fields = ("participant", "subject")


@admin.register(AdminToolCard)
class AdminToolCardAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "url", "order", "icon", "color", "updated_at")
    list_filter = ("section",)
    list_editable = ("section", "order")
    search_fields = ("name", "desc", "url")
    ordering = ("section", "order", "id")


@admin.register(ScheduleRoom)
class ScheduleRoomAdmin(admin.ModelAdmin):
    list_display = (
        "name", "icon", "display_order",
        "sat_morning_class", "sat_afternoon_class",
        "sun_morning_class", "sun_afternoon_class", "is_active",
    )
    list_editable = ("display_order", "is_active")
    autocomplete_fields = (
        "sat_morning_class", "sat_afternoon_class",
        "sun_morning_class", "sun_afternoon_class",
    )
    ordering = ("display_order", "id")


@admin.register(ScheduleExamCountdown)
class ScheduleExamCountdownAdmin(admin.ModelAdmin):
    list_display = ("grade_label", "exam_date", "note", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    ordering = ("display_order", "exam_date")


class DailyScheduleCellInline(admin.TabularInline):
    model = DailyScheduleCell
    extra = 0
    autocomplete_fields = ("tutoring_class", "subject_template", "tutor")


@admin.register(DailySchedule)
class DailyScheduleAdmin(admin.ModelAdmin):
    list_display = ("date", "title_note", "updated_at")
    date_hierarchy = "date"
    inlines = (DailyScheduleCellInline,)


@admin.register(OnlineCourseVideo)
class OnlineCourseVideoAdmin(admin.ModelAdmin):
    list_display = ("title", "course_key", "note", "display_order", "is_active", "updated_at")
    list_editable = ("display_order", "is_active")
    list_filter = ("course_key", "is_active")
    search_fields = ("title", "note", "drive_url")
    ordering = ("course_key", "display_order", "-created_at")


@admin.register(StarQuiz)
class StarQuizAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "grade_level", "subject_tag", "star_reward", "publish_at", "expires_at", "is_active")
    list_filter = ("grade_level", "is_active")
    search_fields = ("code", "title", "subject_tag")
    ordering = ("-publish_at",)


class StarQuizChoiceInline(admin.TabularInline):
    model = StarQuizChoice
    extra = 0


@admin.register(StarQuizQuestion)
class StarQuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "question_type", "points", "correct_choice_index")
    list_filter = ("question_type", "quiz")
    search_fields = ("question_text", "quiz__code", "quiz__title")
    inlines = (StarQuizChoiceInline,)
    autocomplete_fields = ("quiz",)


@admin.register(StarQuizChoice)
class StarQuizChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "order", "text")
    search_fields = ("text", "question__question_text")
    autocomplete_fields = ("question",)


@admin.register(StarQuizAttempt)
class StarQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("quiz", "student", "score_points", "max_points", "stars_awarded", "is_graded", "submitted_at")
    list_filter = ("is_graded", "quiz")
    search_fields = ("quiz__code", "quiz__title", "student__full_name", "student__nickname")
    autocomplete_fields = ("quiz", "student")
    ordering = ("-submitted_at",)


@admin.register(StarQuizAnswer)
class StarQuizAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "points_awarded")
    search_fields = ("attempt__student__full_name", "question__question_text")
    autocomplete_fields = ("attempt", "question", "selected_choice")



# ---------------------------------------------------------
# Revenue & Cost Analysis
# ---------------------------------------------------------
class CostScenarioFixedCostInline(admin.TabularInline):
    model = CostScenarioFixedCost
    extra = 1


class CostScenarioClassInline(admin.TabularInline):
    model = CostScenarioClass
    extra = 0
    autocomplete_fields = ("tutoring_class",)


@admin.register(CostScenario)
class CostScenarioAdmin(admin.ModelAdmin):
    list_display = ("name", "period_month", "allocation_method", "updated_at")
    list_filter = ("allocation_method", "period_month")
    search_fields = ("name", "note")
    ordering = ("-period_month",)
    inlines = (CostScenarioFixedCostInline, CostScenarioClassInline)
