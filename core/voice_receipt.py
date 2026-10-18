"""Parse a spoken / typed Thai receipt command into a draft.

Example: "สร้างใบเสร็จต่อคอร์สให้คอปเตอร์ ป.6 เสาร์บ่าย ห้องมะม่วง 10 ครั้ง ยอด 3890 บาท"

Rule-based (no external AI): pulls out the nickname by matching against
students who have an active enrollment, plus grade, time slot, room,
session count and amount, then narrows the matching enrollments.
"""
from __future__ import annotations

import re
from decimal import Decimal

_DIGITS = {"ศูนย์": 0, "หนึ่ง": 1, "เอ็ด": 1, "สอง": 2, "ยี่": 2, "สาม": 3, "สี่": 4, "ห้า": 5,
           "หก": 6, "เจ็ด": 7, "แปด": 8, "เก้า": 9}
_UNITS = {"สิบ": 10, "ร้อย": 100, "พัน": 1000, "หมื่น": 10000, "แสน": 100000}
_THAI_NUM_RE = re.compile("(?:" + "|".join(sorted(list(_DIGITS) + list(_UNITS), key=len, reverse=True)) + ")+")
_THAI_DIGIT_TRANS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

SLOT_WORDS = [
    ("sat_morning", ("เสาร์เช้า",)),
    ("sat_afternoon", ("เสาร์บ่าย",)),
    ("sun_morning", ("อาทิตย์เช้า", "อาทิตเช้า")),
    ("sun_afternoon", ("อาทิตย์บ่าย", "อาทิตบ่าย")),
]


def thai_words_to_number(words: str) -> int | None:
    """'สามพันแปดร้อยเก้าสิบ' -> 3890, 'สิบ' -> 10, 'ยี่สิบเอ็ด' -> 21."""
    total, current, i = 0, 0, 0
    tokens = sorted(list(_DIGITS) + list(_UNITS), key=len, reverse=True)
    while i < len(words):
        tok = next((t for t in tokens if words.startswith(t, i)), None)
        if tok is None:
            return None
        if tok in _DIGITS:
            current = _DIGITS[tok]
        else:
            unit = _UNITS[tok]
            total += (current or 1) * unit
            current = 0
        i += len(tok)
    return total + current


def normalize_numbers(text: str) -> str:
    text = text.translate(_THAI_DIGIT_TRANS)
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    return _THAI_NUM_RE.sub(lambda m: str(thai_words_to_number(m.group(0)) or m.group(0)), text)


def parse_command(text: str) -> dict:
    raw = (text or "").strip()
    norm = normalize_numbers(raw)
    compact = re.sub(r"\s+", "", norm)
    out = {"text": raw, "grade": "", "slot": "", "room_word": "", "sessions": None, "amount": None,
           "action": "renew"}

    m = re.search(r"(ป|ม)\.?\s*([1-6])", norm) or re.search(r"(ประถม|มัธยม)\s*([1-6])", norm)
    if m:
        out["grade"] = ("ป" if m.group(1).startswith("ป") else "ม") + "." + m.group(2)

    for slot, words in SLOT_WORDS:
        if any(w in compact for w in words):
            out["slot"] = slot
            break

    m = re.search(r"ห้อง\s*([^\s\d,]+)", norm)
    if m:
        out["room_word"] = m.group(1).strip()

    m = re.search(r"(\d+)\s*ครั้ง", norm)
    if m:
        out["sessions"] = int(m.group(1))

    m = (re.search(r"(?:ยอด|ราคา|จำนวนเงิน|เงิน)\s*(\d+(?:\.\d+)?)", norm)
         or re.search(r"(\d+(?:\.\d+)?)\s*บาท", norm))
    if m:
        out["amount"] = str(Decimal(m.group(1)))

    if any(w in compact for w in ("สมัครใหม่", "เด็กใหม่", "คอร์สใหม่")):
        out["action"] = "new"
    return out


def find_candidates(parsed: dict, enrollments, rooms) -> tuple[list, list[str]]:
    """Enrollments whose student's nickname appears in the command, narrowed
    by grade / slot / room. Falls back to a looser match (with a warning)
    when a filter would leave nothing."""
    # nicknames may contain number words (แสนดี, พันพัน), so match the raw
    # text as well as the number-normalised one
    compacts = (re.sub(r"\s+", "", parsed["text"]), re.sub(r"\s+", "", normalize_numbers(parsed["text"])))
    warnings: list[str] = []

    def nick(e):
        return re.sub(r"\s+", "", (e.student.nickname or "").strip())

    hits = [e for e in enrollments if len(nick(e)) >= 2 and any(nick(e) in c for c in compacts)]
    if hits:
        # "ปอนด์" should beat "ปอ" when both match
        longest = max(len(nick(e)) for e in hits)
        hits = [e for e in hits if len(nick(e)) == longest] + [e for e in hits if len(nick(e)) < longest and
                not any(nick(e) in nick(o) and nick(o) != nick(e) for o in hits)]
    if not hits:
        return [], ["ไม่พบชื่อเล่นนักเรียนที่มีคอร์สเรียนอยู่ในคำสั่งนี้"]

    room_classes = None
    if parsed["room_word"]:
        word = parsed["room_word"]
        matched = [r for r in rooms if word in (r.name or "")]
        if matched:
            room_classes = set()
            for r in matched:
                for attr in ("sat_morning_class_id", "sat_afternoon_class_id", "sun_morning_class_id", "sun_afternoon_class_id"):
                    if parsed["slot"] and not attr.startswith(parsed["slot"]):
                        continue
                    cid = getattr(r, attr, None)
                    if cid:
                        room_classes.add(cid)
        else:
            warnings.append(f"ไม่พบห้อง “{word}” ในระบบ")

    def grade_ok(e):
        g = parsed["grade"]
        if not g:
            return True
        name = (e.tutoring_class.name or "").replace(" ", "")
        sg = (e.student.grade_level or "").replace(" ", "")
        return g in name or g.replace(".", "") in name or sg == g

    filters = [
        ("ระดับชั้น", grade_ok),
        ("รอบเวลา", lambda e: not parsed["slot"] or e.tutoring_class.time_slot == parsed["slot"]),
        ("ห้อง", lambda e: room_classes is None or e.tutoring_class_id in room_classes),
    ]
    current = hits
    for label, fn in filters:
        narrowed = [e for e in current if fn(e)]
        if narrowed:
            current = narrowed
        elif current:
            warnings.append(f"ไม่มีคนที่ตรงกับ{label}ที่สั่ง — แสดงทุกคนที่ชื่อตรงกันแทน")
    return current, warnings
