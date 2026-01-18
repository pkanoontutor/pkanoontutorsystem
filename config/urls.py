from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin
    path("adminlublub/", admin.site.urls),

    # Core app (dashboard, student-portal, ฯลฯ)
    path("", include("core.urls")),
]

# ✅ serve media files ตอน DEBUG (จำเป็นสำหรับ profile_image)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
