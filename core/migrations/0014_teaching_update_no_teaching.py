from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_tutor_teaching_update_module'),
    ]

    operations = [
        migrations.AddField(
            model_name='teachingprogressupdate',
            name='no_teaching',
            field=models.BooleanField(default=False, verbose_name='สัปดาห์นี้ไม่มีสอน'),
        ),
    ]
