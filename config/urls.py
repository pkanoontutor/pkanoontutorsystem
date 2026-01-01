from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from core.views import home  # 👈 เพิ่มบรรทัดนี้

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),        # 👈 หน้า Home (www.pkanoontutor.com)
    path("", include("core.urls")),     # 👈 URL อื่น ๆ ของ core (student-portal ฯลฯ)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
