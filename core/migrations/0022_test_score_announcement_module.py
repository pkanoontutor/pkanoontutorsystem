# Generated manually for Pkanoon Tutor test score announcement module
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_sheet_grade_level'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestRound',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='ชื่อรอบสอบ')),
                ('exam_date', models.DateField(blank=True, null=True, verbose_name='วันที่สอบ')),
                ('is_published', models.BooleanField(default=False, verbose_name='เปิดให้ผู้ปกครองดู')),
                ('note', models.TextField(blank=True, verbose_name='หมายเหตุ')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Test Round',
                'verbose_name_plural': 'Test Rounds',
                'ordering': ('-exam_date', '-created_at'),
            },
        ),
        migrations.CreateModel(
            name='TestParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_type', models.CharField(choices=[('student', 'นักเรียนในระบบ'), ('admission', 'จากระบบรับสมัคร'), ('manual', 'กรอกเอง')], default='manual', max_length=20, verbose_name='แหล่งข้อมูล')),
                ('nickname', models.CharField(blank=True, max_length=100, verbose_name='ชื่อเล่น')),
                ('full_name', models.CharField(max_length=255, verbose_name='ชื่อจริงนามสกุล')),
                ('school_name', models.CharField(blank=True, max_length=255, verbose_name='โรงเรียน')),
                ('contact_phone', models.CharField(blank=True, max_length=50, verbose_name='เบอร์ติดต่อ')),
                ('grade_level', models.CharField(blank=True, max_length=50, verbose_name='ระดับชั้น')),
                ('note', models.TextField(blank=True, verbose_name='หมายเหตุ')),
                ('is_active', models.BooleanField(default=True, verbose_name='ใช้งาน')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('admission_inquiry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='test_participations', to='core.admissioninquiry')),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='test_participations', to='core.student')),
                ('test_round', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='core.testround')),
            ],
            options={
                'verbose_name': 'Test Participant',
                'verbose_name_plural': 'Test Participants',
                'ordering': ('test_round', 'full_name', 'nickname'),
            },
        ),
        migrations.CreateModel(
            name='TestSubject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='ชื่อวิชา')),
                ('full_score', models.DecimalField(decimal_places=2, default=100, max_digits=8, verbose_name='คะแนนเต็ม')),
                ('display_order', models.PositiveIntegerField(default=1, verbose_name='ลำดับ')),
                ('is_active', models.BooleanField(default=True, verbose_name='ใช้งาน')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='หมายเหตุ')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('test_round', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subjects', to='core.testround')),
            ],
            options={
                'verbose_name': 'Test Subject',
                'verbose_name_plural': 'Test Subjects',
                'ordering': ('test_round', 'display_order', 'id'),
            },
        ),
        migrations.CreateModel(
            name='TestScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='คะแนนที่ได้')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='หมายเหตุรายวิชา')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scores', to='core.testparticipant')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scores', to='core.testsubject')),
            ],
            options={
                'verbose_name': 'Test Score',
                'verbose_name_plural': 'Test Scores',
                'ordering': ('participant', 'subject__display_order', 'subject_id'),
            },
        ),
        migrations.AddConstraint(
            model_name='testscore',
            constraint=models.UniqueConstraint(fields=('participant', 'subject'), name='uniq_test_score_per_subject'),
        ),
    ]
