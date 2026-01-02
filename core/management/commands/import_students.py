from django.core.management.base import BaseCommand
from core.models import Student, School
from django.db import transaction
from django.utils import timezone
import pandas as pd


class Command(BaseCommand):
    help = "Import students from Excel"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to Excel file")

    def handle(self, *args, **options):
        file_path = options["file"]
        df = pd.read_excel(file_path)

        created, skipped = 0, 0

        with transaction.atomic():
            for i, row in df.iterrows():
                # --- required fields ---
                full_name = row.get("full_name")
                parent_phone = row.get("parent_phone")

                if not full_name or not parent_phone:
                    skipped += 1
                    continue

                # --- school ---
                school = None
                school_name = row.get("school_name")
                if pd.notna(school_name) and str(school_name).strip():
                    school, _ = School.objects.get_or_create(
                        name=str(school_name).strip()
                    )

                # --- enroll date ---
                enroll_date = row.get("enroll_date")
                if pd.isna(enroll_date):
                    enroll_date = timezone.localdate()

                Student.objects.create(
                    full_name=str(full_name).strip(),
                    nickname=str(row.get("nickname") or "").strip(),
                    grade_level=str(row.get("grade_level") or "").strip(),
                    academic_year=str(row.get("academic_year") or "").strip(),
                    school=school,
                    parent_phone=str(parent_phone).strip(),
                    contact_channel=row.get("contact_channel") or "line",
                    enroll_date=enroll_date,
                    referral_source=row.get("referral_source") or "referral",
                    note=str(row.get("note") or "").strip(),
                    is_active=bool(row.get("is_active", True)),
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: {created} created, {skipped} skipped"
            )
        )
