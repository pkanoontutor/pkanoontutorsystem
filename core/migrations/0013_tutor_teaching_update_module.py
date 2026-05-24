# Generated manually for PKanoon Tutor teaching update module
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_course_payment_receipt_module"),
    ]

    operations = [
        migrations.CreateModel(
            name="TeachingTutor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="ชื่อติวเตอร์")),
                ("phone", models.CharField(blank=True, max_length=50, verbose_name="เบอร์ติดต่อ")),
                ("note", models.TextField(blank=True, verbose_name="หมายเหตุ")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
            ],
            options={
                "verbose_name": "Teaching Tutor",
                "verbose_name_plural": "Teaching Tutors",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="TeachingClassSubjectTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject_name", models.CharField(max_length=120, verbose_name="ชื่อวิชา")),
                ("default_sheet_name", models.CharField(blank=True, help_text="ใช้ prefill ให้ติวเตอร์ในแต่ละสัปดาห์", max_length=255, verbose_name="ชื่อชีท/เอกสารตั้งต้น")),
                ("display_order", models.PositiveIntegerField(default=1, verbose_name="ลำดับแสดงผล")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("tutoring_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teaching_subject_templates", to="core.tutoringclass", verbose_name="คลาส")),
            ],
            options={
                "verbose_name": "Teaching Subject Template",
                "verbose_name_plural": "Teaching Subject Templates",
                "ordering": ("tutoring_class__name", "display_order", "subject_name"),
            },
        ),
        migrations.CreateModel(
            name="TeachingWeeklyAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("week_start_date", models.DateField(help_text="ระบบใช้วันเสาร์เป็นต้นสัปดาห์", verbose_name="วันเริ่มสัปดาห์เรียน")),
                ("week_end_date", models.DateField(help_text="ระบบใช้วันอาทิตย์เป็นวันสิ้นสุด", verbose_name="วันสิ้นสุดสัปดาห์เรียน")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("subject_template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="weekly_assignments", to="core.teachingclasssubjecttemplate", verbose_name="วิชาใน template")),
                ("tutor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="weekly_assignments", to="core.teachingtutor", verbose_name="ติวเตอร์")),
                ("tutoring_class", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teaching_weekly_assignments", to="core.tutoringclass", verbose_name="คลาส")),
            ],
            options={
                "verbose_name": "Teaching Weekly Assignment",
                "verbose_name_plural": "Teaching Weekly Assignments",
                "ordering": ("week_start_date", "tutoring_class__name", "subject_template__display_order"),
            },
        ),
        migrations.CreateModel(
            name="TeachingProgressUpdate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("teaching_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="วันที่สอน")),
                ("sheet_name", models.CharField(blank=True, max_length=255, verbose_name="ชื่อชีท/เอกสาร")),
                ("page_to", models.CharField(blank=True, max_length=50, verbose_name="สอนถึงหน้า")),
                ("question_to", models.CharField(blank=True, max_length=50, verbose_name="สอนถึงข้อ")),
                ("updated_by_name", models.CharField(blank=True, max_length=120, verbose_name="ผู้บันทึก")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="อัปเดตล่าสุด")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="วันที่สร้าง")),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="progress_updates", to="core.teachingweeklyassignment", verbose_name="Assignment")),
            ],
            options={
                "verbose_name": "Teaching Progress Update",
                "verbose_name_plural": "Teaching Progress Updates",
                "ordering": ("-teaching_date", "-updated_at"),
            },
        ),
        migrations.AddConstraint(
            model_name="teachingclasssubjecttemplate",
            constraint=models.UniqueConstraint(fields=("tutoring_class", "subject_name"), name="uniq_teaching_subject_per_class"),
        ),
        migrations.AddConstraint(
            model_name="teachingweeklyassignment",
            constraint=models.UniqueConstraint(fields=("week_start_date", "subject_template"), name="uniq_teaching_assignment_per_week_subject"),
        ),
        migrations.AddConstraint(
            model_name="teachingprogressupdate",
            constraint=models.UniqueConstraint(fields=("assignment", "teaching_date"), name="uniq_teaching_progress_per_assignment_date"),
        ),
    ]
