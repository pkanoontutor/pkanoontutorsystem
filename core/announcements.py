"""Announcement image builder: everything is drawn client-side on a canvas."""
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def announcement_builder(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        return HttpResponse(status=403)
    return render(request, "core/announcement_builder.html")
