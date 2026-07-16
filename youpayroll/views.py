import logging
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views import View
from graphene_file_upload.django import FileUploadGraphQLView
from rest_framework.exceptions import AuthenticationFailed
from youpayroll.authentication import CookieKnoxAuthentication

logger = logging.getLogger(__name__)

class LivenessCheck(View):
    """Simple process check (no DB dependency)"""
    http_method_names = ['get']
    def get(self, request, *args, **kwargs):
        return HttpResponse("OK", status=200)

class ReadinessCheck(View):
    """Dependency check (DB)"""
    http_method_names = ['get']
    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return HttpResponse("OK", status=200)
        except Exception:
            logger.exception("Readiness check failed")
            return HttpResponse("Service Unavailable", status=503)

class LegacyHealthCheck(LivenessCheck):
    """
    Compatibility endpoint for /health/ which is used by ALB health checks.

    Kubernetes probes use split endpoints in Helm values:
    /health/live/ for startup/liveness and /health/ready/ for readiness.
    Keep this legacy path lightweight so ALB health checks do not depend on
    transient database availability.
    """
    pass


class DRFTokenAuthGraphQLView(FileUploadGraphQLView):
    """
    A custom GraphQL view that enforces Knox token authentication via CookieKnoxAuthentication.
    Accepts the token from the Authorization header (no CSRF check required) or from the
    auth_token HttpOnly cookie (CSRF enforced for unsafe methods). Ignores session auth
    entirely and returns HTTP 401 if credentials are missing or invalid.
    """
    def dispatch(self, request, *args, **kwargs):
        # CORS preflight OPTIONS requests are sent without authorization headers; bypass token auth.
        if request.method == 'OPTIONS':
            return super().dispatch(request, *args, **kwargs)

        authenticator = CookieKnoxAuthentication()
        try:
            auth_res = authenticator.authenticate(request)
            if auth_res is not None:
                request.user, request.auth = auth_res
            else:
                return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
        except AuthenticationFailed:
            return JsonResponse({"detail": "Invalid authentication credentials."}, status=401)
        except Exception:
            logger.exception("Unexpected GraphQL token authentication error")
            return JsonResponse({"detail": "Internal server error."}, status=500)
        return super().dispatch(request, *args, **kwargs)
