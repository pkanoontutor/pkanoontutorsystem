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

# ✅ สำคัญ: serve MEDIA เสมอ (ไม่ผูกกับ DEBUG)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
