# Generated manually to fix production DB after weekly test module update.
# This migration DOES NOT create WeeklyTest / WeeklyTestScore again.
# It only syncs the existing core_weeklytest table with the current model.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0025_weekly_test_module"),
    ]

    operations = [
        migrations.RunSQL(
            sql=r"""
            ALTER TABLE core_weeklytest
            ADD COLUMN IF NOT EXISTS grade_level varchar(20) NOT NULL DEFAULT 'p4';

            ALTER TABLE core_weeklytest
            DROP CONSTRAINT IF EXISTS uniq_weekly_test_per_week;

            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'uniq_weekly_test_per_week_grade'
                ) THEN
                    ALTER TABLE core_weeklytest
                    ADD CONSTRAINT uniq_weekly_test_per_week_grade
                    UNIQUE (week_start, grade_level);
                END IF;
            END $$;
            """,
            reverse_sql=r"""
            ALTER TABLE core_weeklytest
            DROP CONSTRAINT IF EXISTS uniq_weekly_test_per_week_grade;

            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'uniq_weekly_test_per_week'
                ) THEN
                    ALTER TABLE core_weeklytest
                    ADD CONSTRAINT uniq_weekly_test_per_week
                    UNIQUE (week_start);
                END IF;
            END $$;

            ALTER TABLE core_weeklytest
            DROP COLUMN IF EXISTS grade_level;
            """,
        ),
    ]
