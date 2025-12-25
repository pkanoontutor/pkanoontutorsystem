from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils import timezone

from .models import (
    Student,
    TutoringClass,
    Subject,
    Sheet,
    ClassSubject,
    Enrollment,
    Attendance,
    EnrollmentInstallment,
    SheetInventory,
)


# -----------------------
# Student (Form for prefill student_code)
# -----------------------
class StudentAdminForm(forms.ModelForm):
    # แสดงในฟอร์ม แต่ disable ไม่ให้แก้
    student_code = forms.CharField(label="รหัสนักเรียน", required=False, disabled=True)

    class Meta:
        model = Student
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # หน้า Add (ยังไม่มี pk) → prefill ตัวอย่างรหัส
        if not self.instance.pk:
            yy = str(timezone.localdate().year)[-2:]
            try:
                preview = Student._next_student_code_for_year(yy)
            except Exception:
                preview = ""
            self.fields["student_code"].initial = preview
        else:
            # หน้า Edit → โชว์รหัสจริง
            self.fields["student_code"].initial = getattr(self.instance, "student_code", "")


# -----------------------
# Student
# -----------------------
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm

    list_display = (
        "id",
        "nickname",
        "full_name",
        "grade_level",
        "profile_image_thumb",
        "parent_phone",
        "is_active",
    )
    search_fields = ("nickname", "full_name", "parent_phone")
    list_filter = ("grade_level", "is_active")
    list_per_page = 50

    readonly_fields = ("profile_image_thumb_large",)

    fieldsets = (
        ("รูปโปรไฟล์", {"fields": ("profile_image", "profile_image_thumb_large")}),
        ("ข้อมูลนักเรียน", {"fields": ("nickname", "full_name", "grade_level", "parent_phone", "is_active")}),
    )

    def profile_image_thumb(self, obj):
        if getattr(obj, "profile_image", None):
            return mark_safe(f'<img src="{obj.profile_image.url}" style="width:40px;height:40px;border-radius:999px;object-fit:cover;border:1px solid #e5e7eb;" />')
        return "-"
    profile_image_thumb.short_description = "รูป"

    def profile_image_thumb_large(self, obj):
        if getattr(obj, "profile_image", None):
            return mark_safe(f'<img src="{obj.profile_image.url}" style="width:160px;height:160px;border-radius:18px;object-fit:cover;border:1px solid #e5e7eb;" />')
        return "ยังไม่มีรูป"
    profile_image_thumb_large.short_description = ""
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)
    ordering = ("name",)


@admin.register(Sheet)
class SheetAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "subject", "total_pages", "total_questions", "is_active")
    search_fields = ("code", "title")
    list_filter = ("subject", "is_active")
    ordering = ("subject__name", "code")
    autocomplete_fields = ("subject",)


# -----------------------
# ClassSubject inline within Class
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

    def save_model(self, request, obj, form, change):
        obj.updated_at = timezone.now()
        obj.updated_by = request.user
        # ถ้าอยากให้ last_teacher auto จาก user ก็ทำเพิ่มได้ภายหลัง
        super().save_model(request, obj, form, change)


# -----------------------
# Classes
# -----------------------
@admin.register(TutoringClass)
class TutoringClassAdmin(admin.ModelAdmin):
    list_display = ("name", "total_seats", "course_price", "hours_per_session", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)
    inlines = (ClassSubjectInline,)


# -----------------------
# ClassSubject (optional menu for bulk edit)
# -----------------------
@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = (
        "tutoring_class",
        "subject",
        "current_sheet",
        "current_page",
        "current_question",
        "progress",
        "last_teacher",
        "updated_at",
        "updated_by",
        "is_active",
    )
    list_filter = ("tutoring_class", "subject", "is_active")
    search_fields = (
        "tutoring_class__name",
        "subject__name",
        "current_sheet__code",
        "current_sheet__title",
        "last_teacher",
    )
    autocomplete_fields = ("tutoring_class", "subject", "current_sheet")
    readonly_fields = ("updated_at", "updated_by")
    ordering = ("tutoring_class__name", "subject__name")

    @admin.display(description="Progress (%)")
    def progress(self, obj: ClassSubject):
        return obj.progress_percent()

    def save_model(self, request, obj, form, change):
        obj.updated_at = timezone.now()
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# -----------------------
# Enrollment + Installments
# -----------------------
class EnrollmentInstallmentInline(admin.TabularInline):
    model = EnrollmentInstallment
    extra = 0
    fields = ("installment_no", "amount_due", "amount_paid", "is_paid", "paid_at", "note")
    readonly_fields = ("is_paid", "paid_at")
    ordering = ("installment_no",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "tutoring_class",
        "enrollment_type",
        "is_active",
        "payment_type",
        "installments_count",
        "course_price",
        "discount_amount",
        "net_price",
        "sessions_total",
        "used",
        "remaining",
        "created_at",
    )
    list_filter = ("tutoring_class", "enrollment_type", "is_active", "payment_type")
    search_fields = ("student__full_name", "student__nickname", "tutoring_class__name")
    ordering = ("-created_at",)
    radio_fields = {"enrollment_type": admin.VERTICAL}
    autocomplete_fields = ("student", "tutoring_class")
    inlines = (EnrollmentInstallmentInline,)

    fieldsets = (
        ("ข้อมูลคอร์ส", {"fields": ("student", "tutoring_class", "enrollment_type", "sessions_total", "remark", "is_active")}),
        ("การชำระเงิน", {"fields": ("payment_type", "installments_count", "course_price", "discount_amount", "net_price")}),
        ("จบคอร์ส", {"fields": ("closed_reason", "closed_at")}),
        ("แจ้งเตือนใกล้ครบ", {"fields": ("notified_near_complete", "notified_method", "notified_at")}),
    )

    @admin.display(description="Used (ครั้ง)")
    def used(self, obj: Enrollment):
        return obj.used_sessions()

    @admin.display(description="Remaining (ครั้ง)")
    def remaining(self, obj: Enrollment):
        return obj.remaining_sessions()


@admin.register(EnrollmentInstallment)
class EnrollmentInstallmentAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "installment_no", "amount_due", "amount_paid", "is_paid", "paid_at")
    list_filter = ("is_paid",)
    search_fields = ("enrollment__student__full_name", "enrollment__tutoring_class__name")
    ordering = ("-created_at", "enrollment_id", "installment_no")
    autocomplete_fields = ("enrollment",)


# -----------------------
# Attendance
# -----------------------
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("attendance_date", "student", "enrollment", "status", "deducted", "checked_at")
    list_filter = ("attendance_date", "status", "deducted")
    search_fields = ("student__full_name", "enrollment__tutoring_class__name")
    ordering = ("-attendance_date", "-checked_at")
    autocomplete_fields = ("student", "enrollment")


# -----------------------
# ✅ Sheet Inventory
# -----------------------
@admin.register(SheetInventory)
class SheetInventoryAdmin(admin.ModelAdmin):
    list_display = ("sheet", "quantity", "is_finished", "finished_at", "updated_at")
    list_filter = ("is_finished", "sheet__subject")
    search_fields = ("sheet__code", "sheet__title")
    autocomplete_fields = ("sheet",)
    ordering = ("sheet__code",)
    readonly_fields = ("updated_at",)
