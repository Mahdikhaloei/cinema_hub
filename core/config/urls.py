from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import URLPattern, URLResolver, include, path
from django.views import defaults as default_views


TURLList = list[URLPattern | URLResolver]


urlpatterns: TURLList = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("system-check/", lambda request: JsonResponse({"status": "ok", "version": "1.0.1"})),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = urlpatterns + [path("__debug__/", include(debug_toolbar.urls))]
