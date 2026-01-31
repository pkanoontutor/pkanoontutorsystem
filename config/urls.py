from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from core import views as core_views

urlpatterns = [
    # หน้าแรกของเว็บ (public)
    path("", core_views.home, name="site_home"),

    # Admin (ซ่อน path ตามที่ตั้งไว้)
    path("adminlublub/", admin.site.urls),

    # Core app
    path("", include("core.urls")),
]

# -------------------------------------------------------------------
# ✅ Serve MEDIA files
# -------------------------------------------------------------------
# - DEV: DEBUG=True → Django เสิร์ฟ /media/
# - PROD (Render): ตั้ง env SERVE_MEDIA=1 → Django เสิร์ฟ /media/ จาก persistent disk
#
# ต้องใช้คู่กับ:
#   MEDIA_URL=/media/
#   MEDIA_ROOT=/var/data/media
# -------------------------------------------------------------------
if settings.DEBUG or getattr(settings, "SERVE_MEDIA", False):
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
