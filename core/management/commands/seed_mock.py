from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Student,
    TutoringClass,
    Subject,
    Sheet,
    ClassSubject,
    Enrollment,
)

class Command(BaseCommand):
    help = "Seed mock data for testing (students/classes/sheets/classsubject/enrollments)"

    def handle(self, *args, **options):
        # ---- 1) Subjects ----
        subjects = {}
        for name in ["คณิต", "อังกฤษ", "วิทย์"]:
            obj, _ = Subject.objects.get_or_create(name=name, defaults={"is_active": True})
            subjects[name] = obj

        # ---- 2) Sheets ----
        # (subject, code, title, total_pages, total_questions)
        sheets_data = [
            ("คณิต", "MATH-A01", "เศษส่วนพื้นฐาน", 48, 120),
            ("คณิต", "MATH-A02", "ทศนิยม & ร้อยละ", 52, 140),
            ("คณิต", "MATH-A03", "สมการง่าย ๆ", 40, 100),

            ("อังกฤษ", "ENG-G01", "Grammar Basics", 36, 90),
            ("อังกฤษ", "ENG-R01", "Reading Practice", 60, 0),
            ("อังกฤษ", "ENG-V01", "Vocabulary Set 1", 30, 0),

            ("วิทย์", "SCI-P01", "พืชและการสังเคราะห์แสง", 44, 80),
            ("วิทย์", "SCI-F01", "แรงและการเคลื่อนที่", 50, 100),
        ]

        sheets = {}
        for subj_name, code, title, pages, questions in sheets_data:
            obj, _ = Sheet.objects.get_or_create(
                code=code,
                defaults={
                    "title": title,
                    "subject": subjects[subj_name],
                    "total_pages": pages,
                    "total_questions": questions,
                    "is_active": True,
                },
            )
            # ถ้ามีอยู่แล้ว อัปเดตบางอย่างให้ตรง (optional)
            if obj.subject_id != subjects[subj_name].id:
                obj.subject = subjects[subj_name]
            obj.title = title
            obj.total_pages = pages
            obj.total_questions = questions
            obj.is_active = True
            obj.save()
            sheets[code] = obj

        # ---- 3) Classes ----
        classes_data = [
            ("ป.6 เสาร์บ่าย", 12000, 3.00),
            ("ม.2 อาทิตย์เช้า", 15000, 3.00),
            ("ม.3 พุธเย็น", 18000, 3.00),
        ]

        classes = {}
        for name, price, hrs in classes_data:
            obj, _ = TutoringClass.objects.get_or_create(
                name=name,
                defaults={"course_price": price, "hours_per_session": hrs, "is_active": True},
            )
            obj.course_price = price
            obj.hours_per_session = hrs
            obj.is_active = True
            obj.save()
            classes[name] = obj

        # ---- 4) ClassSubject (นี่แหละที่ใช้ใน Sheet Update) ----
        # map: class -> list of (subject, current_sheet_code, current_page, current_question, last_teacher)
        class_subject_map = {
            "ป.6 เสาร์บ่าย": [
                ("คณิต", "MATH-A01", 10, 25, "ครูบีม"),
                ("อังกฤษ", "ENG-G01", 6, 12, "ครูปังปอนด์"),
                ("วิทย์", "SCI-P01", 8, 15, "ครูอีม"),
            ],
            "ม.2 อาทิตย์เช้า": [
                ("คณิต", "MATH-A02", 18, 40, "ครูบีม"),
                ("อังกฤษ", "ENG-R01", 12, 0, "ครูต้นข้าว"),
                ("วิทย์", "SCI-F01", 14, 30, "ครูอีม"),
            ],
            "ม.3 พุธเย็น": [
                ("คณิต", "MATH-A03", 20, 55, "ครูบีม"),
                ("อังกฤษ", "ENG-V01", 9, 0, "ครูปังปอนด์"),
            ],
        }

        for class_name, rows in class_subject_map.items():
            cls = classes[class_name]
            for subj_name, sheet_code, page, q, teacher in rows:
                subj = subjects[subj_name]
                sh = sheets.get(sheet_code)

                cs, created = ClassSubject.objects.get_or_create(
                    tutoring_class=cls,
                    subject=subj,
                    defaults={
                        "current_sheet": sh,
                        "current_page": page,
                        "current_question": q,
                        "last_teacher": teacher,
                        "is_active": True,
                        "updated_at": timezone.now(),
                        "updated_by": None,
                    },
                )
                # อัปเดตให้ตรงทุกครั้ง
                cs.current_sheet = sh
                cs.current_page = page
                cs.current_question = q
                cs.last_teacher = teacher
                cs.is_active = True
                cs.updated_at = timezone.now()
                cs.save()

        # ---- 5) Students ----
        # สร้างนักเรียนแบบหลากหลาย (student_code จะ generate อัตโนมัติจาก save())
        students_data = [
            # full_name, nickname, grade_level, academic_year, school_name, parent_phone, contact_channel, referral_source
            ("ด.ช.ณัฐดนัย ศรีสุข", "หมิง", "ป.6", "2568", "โรงเรียนสาธิต", "0811111111", "line", "referral"),
            ("ด.ญ.ดารินทร์ พงศ์ดี", "ดอลล่า", "ป.6", "2568", "โรงเรียนสาธิต", "0822222222", "facebook", "facebook"),
            ("ด.ญ.อลิษา วัฒน์ชัย", "อลิษ", "ป.6", "2568", "โรงเรียนสาธิต", "0833333333", "line", "walkin"),
            ("ด.ช.ภัทรดนัย ชูศรี", "เฟิร์ส", "ป.6", "2568", "โรงเรียนสาธิต", "0844444444", "line", "referral"),
            ("ด.ช.โอภาส พิชัย", "โอโร่", "ป.6", "2568", "โรงเรียนสาธิต", "0855555555", "facebook", "google"),

            ("ด.ช.กิตติพงศ์ จันทร์ดี", "กิต", "ม.2", "2568", "โรงเรียนมัธยม A", "0866666666", "line", "flyer"),
            ("ด.ญ.พิมพ์ชนก กาญจนา", "พิม", "ม.2", "2568", "โรงเรียนมัธยม A", "0877777777", "facebook", "referral"),
            ("ด.ช.ธีรภัทร สายใจ", "ธีร์", "ม.2", "2568", "โรงเรียนมัธยม A", "0888888888", "line", "walkin"),
            ("ด.ญ.ชลธิชา แสงทอง", "ชล", "ม.2", "2568", "โรงเรียนมัธยม A", "0899999999", "line", "facebook"),

            ("ด.ช.จิรายุส วงศ์ดี", "จิม", "ม.3", "2568", "โรงเรียนมัธยม B", "0800000001", "facebook", "referral"),
            ("ด.ญ.กวินทร์ณี พัฒน์", "กวิน", "ม.3", "2568", "โรงเรียนมัธยม B", "0800000002", "line", "google"),
            ("ด.ช.ปุณณวิชญ์ เกษม", "ปุณ", "ม.3", "2568", "โรงเรียนมัธยม B", "0800000003", "line", "walkin"),
        ]

        created_students = []
        for full, nick, grade, ay, school, phone, channel, ref in students_data:
            # กันสร้างซ้ำด้วย parent_phone + full_name (ปรับได้)
            st = Student.objects.filter(full_name=full, parent_phone=phone).first()
            if not st:
                st = Student(
                    full_name=full,
                    nickname=nick,
                    grade_level=grade,
                    academic_year=ay,
                    school_name=school,
                    parent_phone=phone,
                    contact_channel=channel,
                    enroll_date=timezone.localdate(),
                    referral_source=ref,
                    is_active=True,
                )
                st.save()
                created_students.append(st)

        # ---- 6) Enrollments ----
        # จับนักเรียนเข้าคลาสตามชั้น
        def pick_class_for_grade(grade_level: str) -> TutoringClass:
            if grade_level.startswith("ป.6"):
                return classes["ป.6 เสาร์บ่าย"]
            if grade_level.startswith("ม.2"):
                return classes["ม.2 อาทิตย์เช้า"]
            return classes["ม.3 พุธเย็น"]

        # สร้าง enrollment ให้คนที่ยังไม่มี
        for st in Student.objects.all():
            cls = pick_class_for_grade(st.grade_level or "")
            existing = Enrollment.objects.filter(student=st, tutoring_class=cls).exists()
            if existing:
                continue

            # สุ่มประเภทให้ดูหลากหลาย (fixed pattern)
            if st.nickname in ["หมิง", "ดอลล่า", "อลิษ"]:
                etype = Enrollment.EnrollmentType.NORMAL_10
            elif st.nickname in ["เฟิร์ส", "โอโร่"]:
                etype = Enrollment.EnrollmentType.FIRST_TRIAL_11
            elif st.grade_level.startswith("ม.2"):
                etype = Enrollment.EnrollmentType.NORMAL_20
            else:
                etype = Enrollment.EnrollmentType.FIRST_BONUS_12

            e = Enrollment(
                student=st,
                tutoring_class=cls,
                enrollment_type=etype,
                payment_type=Enrollment.PaymentType.FULL,
                installments_count=1,
                discount_amount=0,
                remark="Mock data",
                is_active=True,
            )
            # save() จะ snapshot ราคา/คำนวณ net_price ให้เอง
            e.save()

        self.stdout.write(self.style.SUCCESS("✅ Seed mock data completed!"))
        self.stdout.write("Try: /admin and your Dashboard + Sheet Update page.")
