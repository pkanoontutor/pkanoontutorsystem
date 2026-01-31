from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from core import views as core_views

urlpatterns = [
    # หน้าแรกของเว็บ
    path("", core_views.home, name="site_home"),

    # Admin
    path("adminlublub/", admin.site.urls),

    # Core URLs ทั้งหมด
    path("", include("core.urls")),
]

# ✅ Serve MEDIA
# - ใน dev (DEBUG=True) ให้ Django เสิร์ฟ /media/ ได้เลย
# - ใน prod ถ้าต้องการให้ Django เสิร์ฟ /media/ ด้วย ให้ตั้ง env: SERVE_MEDIA=1
if settings.DEBUG or getattr(settings, "SERVE_MEDIA", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
