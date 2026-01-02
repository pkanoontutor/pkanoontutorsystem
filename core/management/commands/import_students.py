from django.core.management.base import BaseCommand
from students.models import Student, School
from django.db import transaction
import pandas as pd

class Command(BaseCommand):
    help = "Import students from Excel"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str)

    def handle(self, *args, **options):
        file_path = options["file"]
        df = pd.read_excel(file_path)

        created, skipped = 0, 0

        with transaction.atomic():
            for i, row in df.iterrows():
                if not row.get("full_name") or not row.get("parent_phone"):
                    skipped += 1
                    continue

                school = None
                if pd.notna(row.get("school_name")):
                    school, _ = School.objects.get_or_create(
                        name=str(row["school_name"]).strip()
                    )

                Student.objects.create(
                    full_name=row["full_name"],
                    nickname=row.get("nickname", "") or "",
                    grade_level=row.get("grade_level", "") or "",
                    academic_year=row.get("academic_year", "") or "",
                    school=school,
                    parent_phone=str(row["parent_phone"]),
                    contact_channel=row.get("contact_channel", "line"),
                    enroll_date=row.get("enroll_date"),
                    referral_source=row.get("referral_source", "referral"),
                    note=row.get("note", "") or "",
                    is_active=bool(row.get("is_active", True)),
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Import complete: {created} created, {skipped} skipped")
        )
