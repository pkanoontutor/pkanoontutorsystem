from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from core import views as core_views

urlpatterns = [
    path("", core_views.home, name="site_home"),
    path("adminlublub/", admin.site.urls),
    path("", include("core.urls")),
]

# ✅ serve media ALWAYS (ไม่ผูกกับ DEBUG)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
