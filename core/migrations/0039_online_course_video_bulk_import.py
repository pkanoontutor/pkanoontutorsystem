# Generated manually for P'Kanoon Tutor
from django.db import migrations

# EP.006-EP.035: the remaining clips from the shared Drive folder
# (https://drive.google.com/drive/folders/157ZPeFIJTF-brx83gJ9WPiywX4okuHkY),
# continuing after EP.001-EP.005 which were already added manually.
# EP number = combined chronological order across all subjects (by recording date).
_SUBJECT_INFO = {
    "คณิตศาสตร์": "พี่มิ้น",
    "วิทยาศาสตร์": "พี่อีม",
    "ภาษาอังกฤษ": "พี่ต้นข้าว",
}

# (ep_number, subject, drive_file_id)
_CLIPS = [
    (6, "ภาษาอังกฤษ", "15w8eysgckur1l72wAsb16UrUH1Y2DFio"),
    (7, "วิทยาศาสตร์", "1j52z4XX-ETlYpgcdShsgKsh-FVqv6pBK"),
    (8, "คณิตศาสตร์", "1AgOV23asOcLZ-boZ3jpltliUVLN_Sxnq"),
    (9, "ภาษาอังกฤษ", "1RYUdmYm4JWt3JSPXOz5se8_NNoX9Pocf"),
    (10, "วิทยาศาสตร์", "1dG4_zG1d00C9x1BIJhSGZcMEXm-TeApX"),
    (11, "คณิตศาสตร์", "1od_cRmpQngbAvGNpOTgAZKQx-EQdx4fD"),
    (12, "ภาษาอังกฤษ", "1ztRgIpBdW8Eedidzr4d3AtoSisU33xqQ"),
    (13, "วิทยาศาสตร์", "1ifz5vzd9mmGY3aKbJLxRzFbH99cp3Km8"),
    (14, "คณิตศาสตร์", "1423Vu9T2BBlj8YGY1qAmboxZQDC5XCT5"),
    (15, "ภาษาอังกฤษ", "1AUkhBUq6qq-c3LJSJQ8q5cnVS8O__vqn"),
    (16, "วิทยาศาสตร์", "1vhCE5ol8sdsk5ctJCh53SokzgvS7T8Jw"),
    (17, "ภาษาอังกฤษ", "1L4iplq5d391JeBoZrTdYlC_Jb2yobAJr"),
    (18, "วิทยาศาสตร์", "1gU35krwNycCBSAbXkytVdc_4hQ4fePSQ"),
    (19, "คณิตศาสตร์", "1jqbkizxD5U269ZDSdfCRPqRj-24keoWB"),
    (20, "ภาษาอังกฤษ", "1YLsuH96GyDnB0hJwmVpva34YIDVYyPbd"),
    (21, "ภาษาอังกฤษ", "1lxN-oKvHirAosR1fujH1kvIUBsekkyqL"),
    (22, "คณิตศาสตร์", "1pN77V8kIA1tLTkXyqnZTIqiDaVypwWVZ"),
    (23, "ภาษาอังกฤษ", "11lR4_P_idZ7upx9fGp51Oxy7xUQqCHn5"),
    (24, "วิทยาศาสตร์", "15AnLToa_56iatfE3HzThISapcITkEGnT"),
    (25, "คณิตศาสตร์", "1iVtylPUjmADo-WoBEzuQBdbsgJzpZVFj"),
    (26, "ภาษาอังกฤษ", "1rt6QBoKckWG7lkowoo6Z-nfZaJUkI9Yq"),
    (27, "วิทยาศาสตร์", "1LN3aENLcmqJTHOMwkmxqszBKHMcn_9e1"),
    (28, "คณิตศาสตร์", "17hcFbDWyJWAip-08OvQbvFE3g0ImI0qs"),
    (29, "ภาษาอังกฤษ", "1pIw3Jo1OLVNSbdhvhTJHmiazNB-FXPq7"),
    (30, "วิทยาศาสตร์", "1gRlA4D8afHX5-7GP0U9XaS5_dpHtAnJD"),
    (31, "คณิตศาสตร์", "1Zeq2UU438woNhVluu3iqoaoJjV9d7pva"),
    (32, "ภาษาอังกฤษ", "1gC7Z1b5eZSjBdYypg0t3MELaaQAyO3ki"),
    (33, "วิทยาศาสตร์", "1TqaRD7ny3TZBX5F7s9l2sX7tfH9ci9qt"),
    (34, "คณิตศาสตร์", "1wIhhMauKQ3CosilqSegV3MpCM79tWo6q"),
    (35, "วิทยาศาสตร์", "1jCb9_cJ4SOqH-db0LS6QdnPaI0TQ1G9j"),
]


def add_clips(apps, schema_editor):
    OnlineCourseVideo = apps.get_model("core", "OnlineCourseVideo")

    existing_max = (
        OnlineCourseVideo.objects.filter(course_key="p6")
        .order_by("-display_order").values_list("display_order", flat=True).first()
    ) or 0

    for i, (ep, subject, file_id) in enumerate(_CLIPS):
        title = f"EP.{ep:03d} {subject}"
        drive_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        if OnlineCourseVideo.objects.filter(course_key="p6", drive_url=drive_url).exists():
            continue
        OnlineCourseVideo.objects.create(
            course_key="p6",
            title=title,
            drive_url=drive_url,
            subject_tag=subject,
            tutor_name=_SUBJECT_INFO.get(subject, ""),
            display_order=existing_max + i + 1,
        )


def remove_clips(apps, schema_editor):
    OnlineCourseVideo = apps.get_model("core", "OnlineCourseVideo")
    ids = [file_id for _ep, _subject, file_id in _CLIPS]
    for file_id in ids:
        OnlineCourseVideo.objects.filter(
            course_key="p6", drive_url=f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0038_onlinecoursevideo_tags"),
    ]

    operations = [
        migrations.RunPython(add_clips, remove_clips),
    ]
