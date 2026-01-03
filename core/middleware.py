from django.http import Http404

class BlockDefaultAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            raise Http404()
        return self.get_response(request)
