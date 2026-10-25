import django.db.models.deletion
from django.db import migrations, models

# Rooms traced on the supplied plans (cropped + mirrored left-right, in
# core/static/core/home_plans/), as % of the image: (floor, name, colour, x, y, w, h)
ROOMS = [
    (1, "ห้องทานข้าว", "#6366f1", 18.56, 21.74, 23.71, 17.39),
    (1, "ห้องนั่งเล่น", "#f97316", 18.56, 48.91, 23.71, 22.83),
    (1, "ห้องรับแขก", "#10b981", 42.68, 21.74, 17.53, 20.65),
    (1, "ห้องน้ำชั้น 1", "#ec4899", 63.92, 21.74, 10.31, 20.65),
    (1, "ห้องครัว", "#0ea5e9", 74.64, 21.74, 20.21, 25.0),
    (1, "โถงชั้น 1", "#eab308", 42.68, 42.61, 41.86, 8.26),
    (1, "บันได", "#8b5cf6", 45.77, 51.3, 8.25, 21.52),
    (1, "โรงจอดรถ", "#ef4444", 55.26, 52.61, 36.49, 44.13),
    (1, "ระเบียงหน้าบ้าน", "#14b8a6", 18.56, 72.83, 29.28, 6.74),
    (1, "ลานซักล้าง", "#64748b", 66.39, 11.96, 19.18, 9.35),
    (1, "สวน", "#84cc16", 2.06, 6.52, 15.46, 89.13),
    (2, "ห้องนอนใหญ่", "#6366f1", 18.14, 43.48, 25.57, 27.17),
    (2, "Walk-in closet", "#f97316", 18.14, 21.74, 19.18, 20.65),
    (2, "ห้องน้ำ 1 (ชั้น 2)", "#10b981", 37.73, 21.74, 11.13, 19.57),
    (2, "ห้องน้ำ 2 (ชั้น 2)", "#ec4899", 49.28, 21.74, 11.75, 19.57),
    (2, "ห้องนอน 2", "#0ea5e9", 61.86, 21.74, 23.09, 21.74),
    (2, "ห้องนอน 3", "#eab308", 61.44, 50.87, 23.51, 21.96),
    (2, "โถงชั้น 2", "#8b5cf6", 44.33, 41.74, 40.62, 8.7),
    (2, "ระเบียงชั้น 2", "#ef4444", 85.57, 19.57, 9.28, 27.17),
]


def seed_rooms(apps, schema_editor):
    Project = apps.get_model("core", "HomeBudgetProject")
    Zone = apps.get_model("core", "HomeBudgetZone")
    project = Project.objects.order_by("id").first() or Project.objects.create()
    existing = {z.name: z for z in Zone.objects.filter(project=project)}
    order = Zone.objects.filter(project=project).count()
    for floor, name, color, x, y, w, h in ROOMS:
        z = existing.get(name)
        if z is None:
            z = Zone(project=project, name=name, color=color, order=order)
            order += 1
        z.floor, z.plan_x, z.plan_y, z.plan_w, z.plan_h = floor, x, y, w, h
        z.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0085_admintoolcard_extras"),
    ]

    operations = [
        migrations.AddField(model_name="homebudgetproject", name="floor_plan_2",
                            field=models.ImageField(blank=True, null=True, upload_to="home_budget/plans/", verbose_name="แปลนบ้าน ชั้น 2")),
        migrations.AlterField(model_name="homebudgetproject", name="floor_plan",
                              field=models.ImageField(blank=True, null=True, upload_to="home_budget/plans/", verbose_name="แปลนบ้าน ชั้น 1")),
        migrations.AddField(model_name="homebudgetzone", name="floor",
                            field=models.PositiveSmallIntegerField(default=1, verbose_name="ชั้น")),
        migrations.RunPython(seed_rooms, migrations.RunPython.noop),
    ]
