# Generated manually for P'Kanoon Tutor
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0039_online_course_video_bulk_import"),
    ]

    operations = [
        migrations.CreateModel(
            name="StarQuiz",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("grade_level", models.CharField(choices=[("p4", "ป.4"), ("p5", "ป.5"), ("p6", "ป.6"), ("m1", "ม.1"), ("m2", "ม.2"), ("m3", "ม.3"), ("m4", "ม.4")], help_text="แสดงเทสนี้ให้เฉพาะนักเรียนระดับชั้นนี้เห็น", max_length=20, verbose_name="ระดับชั้น")),
                ("code", models.CharField(blank=True, help_text="ระบบสร้างให้อัตโนมัติ เช่น ป.6 Test 001", max_length=40, unique=True, verbose_name="รหัสเทส")),
                ("title", models.CharField(max_length=255, verbose_name="ชื่อเทส / หัวข้อ")),
                ("subject_tag", models.CharField(blank=True, max_length=100, verbose_name="วิชา")),
                ("star_reward", models.PositiveIntegerField(default=5, help_text="ดาวที่ได้จะคำนวณตามสัดส่วนคะแนนที่ทำได้ เช่น ได้ 80% ของคะแนน = ได้ 80% ของดาวเต็ม (ปัดเศษ)", verbose_name="ดาวเต็มของเทสนี้")),
                ("publish_at", models.DateTimeField(default=django.utils.timezone.now, help_text="เทสจะเปิดให้ทำตั้งแต่วันเวลานี้เป็นต้นไป (ตั้งล่วงหน้าได้)", verbose_name="วันเผยแพร่")),
                ("expires_at", models.DateTimeField(blank=True, help_text="เว้นว่างได้ถ้าไม่ต้องการวันหมดอายุ", null=True, verbose_name="วันหมดอายุ")),
                ("is_active", models.BooleanField(default=True, verbose_name="เปิดใช้งาน")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Star Quiz",
                "verbose_name_plural": "Star Quizzes",
                "ordering": ("-publish_at", "-id"),
            },
        ),
        migrations.CreateModel(
            name="StarQuizQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=1, verbose_name="ลำดับข้อ")),
                ("question_type", models.CharField(choices=[("mcq", "ข้อกา (ปรนัย)"), ("written", "ข้อเขียน (อัตนัย)")], default="mcq", max_length=20, verbose_name="ประเภทข้อ")),
                ("question_text", models.TextField(verbose_name="โจทย์")),
                ("points", models.PositiveIntegerField(default=1, verbose_name="คะแนนของข้อนี้")),
                ("correct_choice_index", models.PositiveIntegerField(blank=True, null=True, verbose_name="เฉลย (ลำดับช้อยส์ที่ถูก เริ่มที่ 0)")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("quiz", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="core.starquiz")),
            ],
            options={
                "verbose_name": "Star Quiz Question",
                "verbose_name_plural": "Star Quiz Questions",
                "ordering": ("quiz", "order", "id"),
            },
        ),
        migrations.CreateModel(
            name="StarQuizChoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=1, verbose_name="ลำดับช้อยส์")),
                ("text", models.CharField(blank=True, max_length=500, verbose_name="ข้อความช้อยส์")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="choices", to="core.starquizquestion")),
            ],
            options={
                "verbose_name": "Star Quiz Choice",
                "verbose_name_plural": "Star Quiz Choices",
                "ordering": ("question", "order", "id"),
            },
        ),
        migrations.CreateModel(
            name="StarQuizAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("submitted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("score_points", models.PositiveIntegerField(default=0, verbose_name="คะแนนที่ได้")),
                ("max_points", models.PositiveIntegerField(default=0, verbose_name="คะแนนเต็ม")),
                ("stars_awarded", models.PositiveIntegerField(default=0, verbose_name="ดาวที่ได้")),
                ("is_graded", models.BooleanField(default=False, help_text="เป็น False ถ้ามีข้อเขียนที่ยังไม่ได้ตรวจ ดาวจะยังไม่ตัดให้จนกว่าจะตรวจครบ", verbose_name="ตรวจครบแล้ว")),
                ("quiz", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="core.starquiz")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="star_quiz_attempts", to="core.student")),
            ],
            options={
                "verbose_name": "Star Quiz Attempt",
                "verbose_name_plural": "Star Quiz Attempts",
                "ordering": ("-submitted_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="starquizattempt",
            constraint=models.UniqueConstraint(fields=["quiz", "student"], name="uniq_star_quiz_attempt_per_student"),
        ),
        migrations.CreateModel(
            name="StarQuizAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("written_answer", models.TextField(blank=True, verbose_name="คำตอบข้อเขียน")),
                ("points_awarded", models.PositiveIntegerField(blank=True, null=True, verbose_name="คะแนนที่ได้ข้อนี้")),
                ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="core.starquizattempt")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="core.starquizquestion")),
                ("selected_choice", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="core.starquizchoice")),
            ],
            options={
                "verbose_name": "Star Quiz Answer",
                "verbose_name_plural": "Star Quiz Answers",
                "ordering": ("attempt", "question__order"),
            },
        ),
        migrations.AddConstraint(
            model_name="starquizanswer",
            constraint=models.UniqueConstraint(fields=["attempt", "question"], name="uniq_star_quiz_answer_per_question"),
        ),
    ]
