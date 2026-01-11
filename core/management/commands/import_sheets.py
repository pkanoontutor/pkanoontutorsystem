from django.core.management.base import BaseCommand
from django.db import transaction
import pandas as pd

from core.models import Sheet, Subject


class Command(BaseCommand):
    help = "Import Sheet data from CSV / Excel"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to CSV or Excel file (xlsx)",
        )

    def handle(self, *args, **options):
        file_path = options["file"]

        # -----------------------
        # Load file
        # -----------------------
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.lower().endswith(".xlsx"):
            df = pd.read_excel(file_path)
        else:
            self.stderr.write("❌ รองรับเฉพาะ .csv หรือ .xlsx")
            return

        required_cols = {"code", "title", "subject"}
        if not required_cols.issubset(df.columns):
            self.stderr.write(
                f"❌ ไฟล์ต้องมี column: {', '.join(required_cols)}"
            )
            return

        created = 0
        updated = 0
        skipped = 0

        with transaction.atomic():
            for _, row in df.iterrows():
                code = str(row["code"]).strip()
                title = str(row["title"]).strip()
                subject_name = str(row["subject"]).strip()

                if not code or not title or not subject_name:
                    skipped += 1
                    continue

                subject = Subject.objects.filter(name=subject_name, is_active=True).first()
                if not subject:
                    self.stderr.write(f"⚠️ ไม่พบ subject: {subject_name} (code={code})")
                    skipped += 1
                    continue

                sheet, is_created = Sheet.objects.update_or_create(
                    code=code,
                    defaults={
                        "title": title,
                        "subject": subject,
                        "is_active": True,
                    },
                )

                if is_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write("✅ Import completed")
        self.stdout.write(f"  ➕ created: {created}")
        self.stdout.write(f"  ♻️ updated: {updated}")
        self.stdout.write(f"  ⏭ skipped: {skipped}")
