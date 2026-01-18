from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from core.views import home_redirect

urlpatterns = [
    # ✅ หน้าแรกของเว็บ (www.pkanoontutor.com)
    path("", home_redirect, name="home"),

    # Admin
    path("adminlublub/", admin.site.urls),

    # URL ทั้งหมดของ core (dashboard, student-portal, ฯลฯ)
    path("", include("core.urls")),
]

# ✅ serve media files ตอน DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
