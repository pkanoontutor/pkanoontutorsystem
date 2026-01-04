from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_school_remove_enrollment_closed_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tutoringclass',
            name='time_slot',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('sat_morning', 'เสาร์เช้า'),
                    ('sat_afternoon', 'เสาร์บ่าย'),
                    ('sun_morning', 'อาทิตย์เช้า'),
                    ('sun_afternoon', 'อาทิตย์บ่าย'),
                ],
                default='sat_morning',
            ),
        ),
    ]
