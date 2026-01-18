from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from core import views as core_views

urlpatterns = [
    # ✅ หน้าแรกของเว็บให้เป็น Home จริงๆ (Public)
    path("", core_views.home, name="site_home"),

    # Admin
    path("adminlublub/", admin.site.urls),

    # Core app URLs (dashboard, student-portal, ฯลฯ)
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
