"""Bulk-import sheet PDFs (ปก / เนื้อหา / เฉลย) from a folder tree.

Expected layout -- one folder per sheet, named with the sheet code first:

    <root>/ป.6 - 2569/M-P6-01 คณิต ป.6 พื้นฐานเล่ม 1/
        M-P6-01 ... (ปก).pdf
        M-P6-01 ... (เนื้อหา).pdf
        เฉลย M-P6-01 ....pdf

Runs as a dry run by default and prints exactly what it would do; pass
--commit to write. Re-running is safe: a file already attached to the same
sheet under the same kind and filename is skipped rather than duplicated.
"""
from __future__ import annotations

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Sheet, SheetDocument
from core.sheet_pdf_import import (
    attach_document_from_path,
    classify,
    find_sheet_folders,
    render_pdf,
    sheet_code_from_folder,
    sync_sheet_total_pages,
)


class Command(BaseCommand):
    help = "นำเข้าไฟล์ PDF ของชีท (ปก/เนื้อหา/เฉลย) จากโฟลเดอร์เข้าสู่ระบบ"

    def add_arguments(self, parser):
        parser.add_argument("root", help="โฟลเดอร์หลักที่เก็บชีททั้งหมด")
        parser.add_argument("--commit", action="store_true",
                            help="เขียนลงฐานข้อมูลจริง (ค่าเริ่มต้นคือ dry run)")
        parser.add_argument("--grade", default="",
                            help="ทำเฉพาะโฟลเดอร์ระดับชั้นที่ขึ้นต้นด้วยข้อความนี้ เช่น 'ป.6'")
        parser.add_argument("--limit", type=int, default=0,
                            help="จำกัดจำนวนชีทที่ประมวลผล (ใช้ตอนทดลอง)")

    def handle(self, *args, **opts):
        root = opts["root"]
        commit = opts["commit"]
        grade_filter = (opts["grade"] or "").strip()
        limit = opts["limit"]

        if not os.path.isdir(root):
            self.stderr.write(f"ไม่พบโฟลเดอร์: {root}")
            return

        folders = find_sheet_folders(root)
        if grade_filter:
            folders = [f for f in folders if grade_filter in f]
        if limit:
            folders = folders[:limit]

        known = {s.code.upper(): s for s in Sheet.objects.all()}
        stats = {
            "folders": 0, "matched": 0, "no_sheet": 0,
            "created": 0, "skipped": 0, "unreadable": 0, "bytes": 0, "dupes": 0,
        }
        missing_codes: list[str] = []
        touched_sheets: set[int] = set()

        for folder in folders:
            stats["folders"] += 1
            name = os.path.basename(folder)
            code = sheet_code_from_folder(name)

            sheet = known.get(code.upper())
            pdfs = sorted(
                f for f in os.listdir(folder)
                if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(folder, f))
            )
            if not sheet:
                stats["no_sheet"] += 1
                missing_codes.append(code)
                self.stdout.write(f"[ไม่พบชีท] {code} -- มี {len(pdfs)} ไฟล์รออยู่ ({name})")
                continue

            stats["matched"] += 1
            self.stdout.write(f"\n{code} -- {sheet.title}")
            seen_sizes: dict[tuple[str, int], str] = {}
            for fname in pdfs:
                path = os.path.join(folder, fname)
                size = os.path.getsize(path)
                pages, _ = render_pdf(path, thumbnail=False)
                kind, why = classify(fname, pages)
                if pages == 0:
                    stats["unreadable"] += 1

                exists = SheetDocument.objects.filter(
                    sheet=sheet, kind=kind, title=fname
                ).exists()
                if exists:
                    stats["skipped"] += 1
                    self.stdout.write(f"    - {kind:7} {fname[:58]} (มีอยู่แล้ว ข้าม)")
                    continue

                pages_txt = f"{pages} หน้า" if pages else "นับหน้าไม่ได้"
                self.stdout.write(
                    f"    + {kind:7} {fname[:58]} · {size/1024/1024:.1f}MB · {pages_txt} · {why}"
                )
                # Same kind and identical byte size inside one folder is
                # almost always the same document saved twice. Both are
                # imported -- dropping a file silently would be worse -- but
                # it is called out so it can be cleaned up.
                twin = seen_sizes.get((kind, size))
                if twin:
                    stats["dupes"] += 1
                    self.stdout.write(f"        ! ขนาดเท่ากับ '{twin[:48]}' อาจเป็นไฟล์ซ้ำ")
                else:
                    seen_sizes[(kind, size)] = fname
                stats["bytes"] += size

                if commit:
                    attach_document_from_path(sheet, kind, path, fname, page_count=pages)
                    touched_sheets.add(sheet.id)
                stats["created"] += 1

        if commit and touched_sheets:
            with transaction.atomic():
                for sid in touched_sheets:
                    sheet = Sheet.objects.filter(id=sid).first()
                    if sheet:
                        sync_sheet_total_pages(sheet)

        self.stdout.write("\n" + "=" * 60)
        mode = "บันทึกจริง" if commit else "DRY RUN (ยังไม่เขียนอะไร)"
        self.stdout.write(f"โหมด: {mode}")
        self.stdout.write(f"  โฟลเดอร์ชีททั้งหมด : {stats['folders']}")
        self.stdout.write(f"  จับคู่ชีทได้        : {stats['matched']}")
        self.stdout.write(f"  ไม่มีชีทนี้ในระบบ   : {stats['no_sheet']}")
        self.stdout.write(f"  ไฟล์ที่จะนำเข้า     : {stats['created']}")
        self.stdout.write(f"  ไฟล์ที่มีอยู่แล้ว    : {stats['skipped']}")
        self.stdout.write(f"  นับจำนวนหน้าไม่ได้  : {stats['unreadable']}")
        self.stdout.write(f"  น่าจะเป็นไฟล์ซ้ำ    : {stats['dupes']}")
        self.stdout.write(f"  ขนาดรวม             : {stats['bytes']/1024/1024/1024:.2f} GB")
        if missing_codes:
            self.stdout.write(
                "\nรหัสชีทที่ยังไม่มีในระบบ (ต้องสร้างใน Sheet Inventory ก่อน):\n  "
                + ", ".join(sorted(set(missing_codes)))
            )
        if not commit:
            self.stdout.write("\nถ้าผลข้างบนถูกต้องแล้ว ให้รันซ้ำด้วย --commit เพื่อบันทึกจริง")
