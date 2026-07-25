"""Email the full-system Excel export.

Scheduled to run 23:59 every Sunday and Friday (see render.yaml cron jobs).
Run manually with:  python manage.py email_full_export
"""

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.exports import build_full_workbook


DEFAULT_RECIPIENT = "pkanoontutor@gmail.com"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class Command(BaseCommand):
    help = "Build the full-system Excel export and email it as an attachment."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            action="append",
            dest="recipients",
            help="Recipient email (repeatable). Defaults to %s." % DEFAULT_RECIPIENT,
        )

    def handle(self, *args, **options):
        recipients = options.get("recipients") or [DEFAULT_RECIPIENT]

        if not settings.EMAIL_HOST_PASSWORD:
            # Fail loudly: a silent no-op here would look like a delivered report.
            self.stderr.write(
                self.style.ERROR(
                    "EMAIL_HOST_PASSWORD is not set — cannot send. "
                    "Set it in the environment (Gmail App Password) and retry."
                )
            )
            return

        self.stdout.write("Building workbook…")
        buff, filename = build_full_workbook()
        size_kb = len(buff.getvalue()) / 1024

        now = timezone.localtime()
        subject = f"[Pkanoon Tutor] Export ข้อมูลทั้งระบบ {now.strftime('%d/%m/%Y %H:%M')}"
        body = (
            "รายงาน Export ข้อมูลทั้งระบบอัตโนมัติ\n\n"
            f"สร้างเมื่อ: {now.strftime('%d/%m/%Y %H:%M')}\n"
            f"ไฟล์แนบ: {filename} ({size_kb:,.0f} KB)\n\n"
            "ไฟล์นี้แยกข้อมูลเป็น sheet ตามหมวด เช่น นักเรียน คอร์สเรียน ใบเสร็จรับเงิน "
            "รายจ่ายโรงเรียน ค่าสอนติวเตอร์ คลังชีท และผล Test ย่อย\n"
            "ดู sheet แรก (สรุปภาพรวม) เพื่อดูว่ามีข้อมูลอะไรบ้างและแต่ละหมวดมีกี่แถว\n"
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        email.attach(filename, buff.getvalue(), XLSX_MIME)
        email.send(fail_silently=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {filename} ({size_kb:,.0f} KB) to {', '.join(recipients)}"
            )
        )
