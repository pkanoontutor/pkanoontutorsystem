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
import re
import zlib

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Sheet, SheetDocument

# "เฉลย" wins over everything: an answer key for a cover page is still an
# answer. Otherwise ปก marks a cover, and เนื้อหา/โจทย์ mark content.
_ANSWER_RE = re.compile(r"เฉลย")
_COVER_RE = re.compile(r"(?:^|[\s(\[_-])ปก(?:$|[\s)\]_.-])")
_CONTENT_RE = re.compile(r"เนื้อหา|โจทย์")


def classify(filename: str, page_count: int) -> tuple[str, str]:
    """Return (kind, why) for a PDF filename."""
    stem = os.path.splitext(filename)[0]
    if _ANSWER_RE.search(stem):
        return SheetDocument.Kind.ANSWER, "ชื่อไฟล์มี 'เฉลย'"
    if _COVER_RE.search(stem):
        return SheetDocument.Kind.COVER, "ชื่อไฟล์มี 'ปก'"

    if _CONTENT_RE.search(stem):
        kind, why = SheetDocument.Kind.CONTENT, "ชื่อไฟล์มี 'เนื้อหา/โจทย์'"
    else:
        kind, why = SheetDocument.Kind.CONTENT, "ไม่มีคำบอกประเภท ถือเป็นเนื้อหา"

    # Content runs to dozens or hundreds of pages here, so a single-page file
    # is a cover whatever the name suggests. This matters because words like
    # "โจทย์" also appear in sheet *titles* (e.g. "คณิตตะลุยโจทย์"), which
    # would otherwise file a one-page cover as content and inflate the
    # sheet's page total.
    if page_count == 1:
        return SheetDocument.Kind.COVER, "มีหน้าเดียว จึงถือเป็นปก"
    return kind, why


_PAGE_OBJ_RE = re.compile(rb"/Type\s*/Page(?![s/\w])")


def count_pages(path: str) -> int:
    """Page count without adding a PDF dependency.

    Newer PDFs pack their object definitions into compressed streams, so the
    page objects are not visible in the raw bytes at all -- roughly one file
    in fourteen here. When the plain scan finds nothing, every Flate stream
    is inflated and rescanned, which recovers them. Returns 0 if neither
    works, and the caller reports that rather than storing a wrong number.
    """
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return 0

    pages = len(_PAGE_OBJ_RE.findall(data))
    if pages:
        return pages

    pages = 0
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        try:
            pages += len(_PAGE_OBJ_RE.findall(zlib.decompress(data[start:end])))
        except zlib.error:
            continue        # not Flate, or not a whole stream -- skip it
    if pages:
        return pages

    counts = [int(m.group(1)) for m in re.finditer(rb"/Count\s+(\d+)", data)]
    return max(counts) if counts else 0


def sheet_code_from_folder(name: str) -> str:
    """Folder names lead with the code: 'M-P6-01 คณิต ...' -> 'M-P6-01'."""
    parts = (name or "").strip().split()
    if not parts:
        return ""
    code = parts[0]
    # A code is ASCII letters/digits/dashes; a Thai first word means the
    # folder is a grouping folder, not a sheet.
    return code if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-]*", code) else ""


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

        folders = self._sheet_folders(root, grade_filter)
        if limit:
            folders = folders[:limit]

        known = {s.code.upper(): s for s in Sheet.objects.all()}
        stats = {
            "folders": 0, "matched": 0, "no_code": 0, "no_sheet": 0,
            "created": 0, "skipped": 0, "unreadable": 0, "bytes": 0, "dupes": 0,
        }
        missing_codes: list[str] = []
        touched_sheets: set[int] = set()

        for folder in folders:
            stats["folders"] += 1
            name = os.path.basename(folder)
            code = sheet_code_from_folder(name)
            if not code:
                stats["no_code"] += 1
                self.stdout.write(f"[ข้าม] {name} -- ไม่พบรหัสชีทที่ต้นชื่อโฟลเดอร์")
                continue

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
                pages = count_pages(path)
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
                    order = (
                        SheetDocument.objects.filter(sheet=sheet, kind=kind).count() + 1
                    )
                    # Store under an ASCII name. Django's filename sanitiser
                    # strips Thai vowel and tone marks, which would turn
                    # "อังกฤษ พื้นฐาน" into "องกฤษ พนฐาน" on disk; the
                    # original filename is kept in `title`, which is what the
                    # UI actually shows.
                    stored = f"{sheet.code}-{kind}-{order}.pdf"
                    with open(path, "rb") as fh:
                        doc = SheetDocument(
                            sheet=sheet, kind=kind, title=fname,
                            page_count=pages, display_order=order,
                        )
                        doc.pdf.save(stored, File(fh), save=True)
                    touched_sheets.add(sheet.id)
                stats["created"] += 1

        if commit and touched_sheets:
            with transaction.atomic():
                for sid in touched_sheets:
                    self._sync_pages(sid)

        self.stdout.write("\n" + "=" * 60)
        mode = "บันทึกจริง" if commit else "DRY RUN (ยังไม่เขียนอะไร)"
        self.stdout.write(f"โหมด: {mode}")
        self.stdout.write(f"  โฟลเดอร์ชีททั้งหมด : {stats['folders']}")
        self.stdout.write(f"  จับคู่ชีทได้        : {stats['matched']}")
        self.stdout.write(f"  ไม่พบรหัสในชื่อ     : {stats['no_code']}")
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

    def _sheet_folders(self, root: str, grade_filter: str) -> list[str]:
        """Sheet folders live one level under each grade folder, with a few
        nested a level deeper inside grouping folders."""
        out: list[str] = []
        for grade in sorted(os.listdir(root)):
            gpath = os.path.join(root, grade)
            if not os.path.isdir(gpath):
                continue
            if grade_filter and not grade.startswith(grade_filter):
                continue
            for entry in sorted(os.listdir(gpath)):
                epath = os.path.join(gpath, entry)
                if not os.path.isdir(epath):
                    continue
                if sheet_code_from_folder(entry):
                    out.append(epath)
                    continue
                # Grouping folder (e.g. คอร์สติวออนไลน์): look one level in.
                for sub in sorted(os.listdir(epath)):
                    spath = os.path.join(epath, sub)
                    if os.path.isdir(spath) and sheet_code_from_folder(sub):
                        out.append(spath)
        return out

    def _sync_pages(self, sheet_id: int) -> None:
        from django.db.models import Sum
        sheet = Sheet.objects.filter(id=sheet_id).first()
        if not sheet:
            return
        total = (
            SheetDocument.objects
            .filter(sheet=sheet, kind=SheetDocument.Kind.CONTENT)
            .aggregate(n=Sum("page_count")).get("n") or 0
        )
        if total and total != int(sheet.total_pages or 0):
            sheet.total_pages = total
            sheet.save(update_fields=["total_pages"])
