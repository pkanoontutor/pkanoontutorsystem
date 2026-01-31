from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import path, include

import os

from core import views as core_views


def media_serve(request, path: str):
    """
    Serve media files from MEDIA_ROOT in production (Render).
    This avoids relying on django.conf.urls.static.static(), which is meant for dev.
    """
    # Normalize path to avoid path traversal
    safe_path = os.path.normpath(path).lstrip("/")

    full_path = os.path.join(settings.MEDIA_ROOT, safe_path)

    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404("Media not found")

    return FileResponse(open(full_path, "rb"))


urlpatterns = [
    # ✅ Serve MEDIA explicitly (works in prod)
    # Enable when SERVE_MEDIA=1 (recommended on Render if you don't have a CDN)
    path("media/<path:path>", media_serve),

    # หน้าแรกของเว็บ (public)
    path("", core_views.home, name="site_home"),

    # Admin
    path("adminlublub/", admin.site.urls),

    # Core app
    path("", include("core.urls")),
]
