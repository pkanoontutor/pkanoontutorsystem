"""Shared PDF-import logic for ปก/เนื้อหา/เฉลย sheet documents.

Used by three entry points so a sheet is classified and stored identically
regardless of how it got here: `manage.py import_sheet_pdfs` (a folder tree
on the admin's own machine), the bulk zip-upload page, and the single-file
drag-and-drop uploader on the Sheet Inventory card.
"""
from __future__ import annotations

import os
import re
from io import BytesIO

from django.core.files.base import ContentFile, File
from django.db.models import Sum

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


def sheet_code_from_folder(name: str) -> str:
    """Folder names lead with the code: 'M-P6-01 คณิต ...' -> 'M-P6-01'."""
    parts = (name or "").strip().split()
    if not parts:
        return ""
    code = parts[0]
    # A code is ASCII letters/digits/dashes; a Thai first word means the
    # folder is a grouping folder, not a sheet.
    return code if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-]*", code) else ""


def find_sheet_folders(root: str) -> list[str]:
    """Recursively find every folder that looks like a sheet folder: its
    name starts with a code and it directly contains at least one PDF.

    Works whatever depth grade or grouping folders are nested at, so the
    same function serves the full archive, a single grade folder, or a zip
    extracted flat -- no fixed-depth assumption needed.
    """
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        name = os.path.basename(dirpath)
        if sheet_code_from_folder(name) and any(f.lower().endswith(".pdf") for f in filenames):
            out.append(dirpath)
            dirnames[:] = []  # a matched sheet folder's own subfolders aren't sheets
    out.sort()
    return out


def _pdfium_input(source):
    """Resolve a path string, an open file handle, or a Django UploadedFile
    into whatever pypdfium2 accepts (a path, or raw bytes)."""
    if isinstance(source, str):
        return source
    temp_path = getattr(source, "temporary_file_path", None)
    if callable(temp_path):
        try:
            return temp_path()
        except Exception:
            pass
    source.seek(0)
    data = source.read()
    source.seek(0)
    return data


def render_pdf(source, *, thumbnail: bool, target_width: int = 700) -> tuple[int, bytes | None]:
    """Open a PDF once and return (page_count, png_bytes_or_None).

    Uses pypdfium2 -- a real PDF renderer, so page counts are exact even for
    files that pack their objects into compressed streams, and rendering
    page 1 of even a 100MB+ file takes a fraction of a second. `source` may
    be a path, an open file handle, or a Django UploadedFile. png_bytes is
    only produced when thumbnail=True (only needed for a ปก); returns
    (0, None) if the file cannot be opened at all.
    """
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return 0, None
    try:
        pdf = pdfium.PdfDocument(_pdfium_input(source))
    except Exception:
        return 0, None

    # A bulk import opens hundreds of these in one process; each PdfDocument
    # holds a native PDFium handle that isn't freed until closed (or until
    # the GC eventually gets to it), so an explicit close matters here more
    # than it would for a one-off call.
    try:
        page_count = len(pdf)
        png = None
        if thumbnail and page_count:
            page = None
            try:
                page = pdf[0]
                w, _h = page.get_size()
                scale = min(target_width / w, 3) if w else 1
                bitmap = page.render(scale=scale)
                buf = BytesIO()
                bitmap.to_pil().save(buf, format="PNG")
                png = buf.getvalue()
            except Exception:
                png = None
            finally:
                if page is not None:
                    page.close()
        return page_count, png
    finally:
        pdf.close()


def attach_document(
    sheet: Sheet,
    kind: str,
    django_file,
    display_filename: str,
    *,
    page_count: int | None = None,
    thumbnail_png: bytes | None = None,
    source_book=None,
    source_url: str = "",
    uploaded_by=None,
) -> SheetDocument:
    """Attach one PDF (already an open Django File) to `sheet`.

    If page_count/thumbnail_png aren't supplied, they're computed here via
    pypdfium2. A ปก replaces any previous cover (row and file) and also
    becomes the sheet's cover_image, so the bookshelf and Sheet Inventory
    show the same picture. Stored under an ASCII filename -- Django's
    sanitiser strips Thai vowel and tone marks -- keeping the real name in
    `title`, which is what the UI shows.
    """
    if page_count is None or (kind == SheetDocument.Kind.COVER and thumbnail_png is None):
        want_thumb = kind == SheetDocument.Kind.COVER
        counted, rendered = render_pdf(django_file, thumbnail=want_thumb)
        if page_count is None:
            page_count = counted
        if want_thumb and thumbnail_png is None:
            thumbnail_png = rendered

    if kind == SheetDocument.Kind.COVER:
        for old in SheetDocument.objects.filter(sheet=sheet, kind=SheetDocument.Kind.COVER):
            old.pdf.delete(save=False)
            if old.thumbnail:
                old.thumbnail.delete(save=False)
            old.delete()
        order = 1
    else:
        order = SheetDocument.objects.filter(sheet=sheet, kind=kind).count() + 1

    stored_name = f"{sheet.code}-{kind}-{order}.pdf"
    doc = SheetDocument(
        sheet=sheet, kind=kind, title=display_filename[:255],
        page_count=page_count or 0, display_order=order,
        source_book=source_book, source_url=(source_url or "")[:2000],
        uploaded_by=uploaded_by,
    )
    doc.pdf.save(stored_name, django_file, save=True)

    if thumbnail_png:
        doc.thumbnail.save(f"{sheet.code}-{doc.id}.png", ContentFile(thumbnail_png), save=True)
        if kind == SheetDocument.Kind.COVER:
            if sheet.cover_image:
                sheet.cover_image.delete(save=False)
            sheet.cover_image.save(f"{sheet.code}.png", ContentFile(thumbnail_png), save=True)

    return doc


def attach_document_from_path(
    sheet: Sheet, kind: str, path: str, display_filename: str, **kwargs
) -> SheetDocument:
    """Path-based convenience wrapper for the CLI importer and the bulk
    zip-upload view, where the source file already sits on local disk."""
    with open(path, "rb") as fh:
        return attach_document(sheet, kind, File(fh), display_filename, **kwargs)


def sync_sheet_total_pages(sheet: Sheet) -> int:
    """Set Sheet.total_pages from its uploaded content PDFs (several add
    up). Returns the sheet's page total unchanged if nothing countable is
    attached, so a PDF whose page count couldn't be read never zeroes out a
    figure entered by hand."""
    total = (
        SheetDocument.objects
        .filter(sheet=sheet, kind=SheetDocument.Kind.CONTENT)
        .aggregate(n=Sum("page_count")).get("n") or 0
    )
    if total and total != int(sheet.total_pages or 0):
        sheet.total_pages = total
        sheet.save(update_fields=["total_pages"])
    return int(sheet.total_pages or 0)
