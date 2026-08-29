
# Generated manually for Pkanoon Tutor: pricing-option (trial-then-enroll vs
# no-trial) on the new-student payment notice.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0061_tutor_sheet_markup"),
    ]

    operations = [
        migrations.AddField(
            model_name="newstudentpaymentnotice",
            name="pricing_option",
            field=models.CharField(
                choices=[("trial_then_enroll", "ทดลองเรียนแล้วสมัคร"), ("no_trial", "สมัครโดยไม่ทดลอง")],
                default="trial_then_enroll",
                max_length=20,
                verbose_name="รูปแบบการสมัคร",
            ),
        ),
    ]
