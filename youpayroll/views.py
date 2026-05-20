import logging
from django.views import View
from django.http import HttpResponse
from django.db import connection

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
    Temporary compatibility endpoint for /health/ which is used by ALB
    and K8s liveness probes. 
    
    DEPRECATION NOTE: The shared central Helm charts currently bind both liveness 
    and readiness probes to a single path (.Values.deployment.containers.default.health.path).
    Consequently, /health/ must remain a liveness check (returning 200 without DB checks) 
    to prevent transient database network blips from killing/restarting active pods.
    
    Once the Helm templates support split endpoints for liveness (path: /liveness/) 
    and readiness (path: /readiness/), this legacy endpoint should be deprecated and removed.
    """
    pass


from graphene_file_upload.django import FileUploadGraphQLView
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

class DRFTokenAuthGraphQLView(FileUploadGraphQLView):
    """
    A custom GraphQL view that enforces token-only authentication using DRF's 
    TokenAuthentication. It bypasses and ignores Django's cookie-based SessionAuthentication 
    to protect the endpoint against CSRF attacks, and returns HTTP 401 response if missing or invalid.
    """
    def dispatch(self, request, *args, **kwargs):
        authenticator = TokenAuthentication()
        try:
            auth_res = authenticator.authenticate(request)
            if auth_res is not None:
                request.user, request.auth = auth_res
            else:
                from django.http import JsonResponse
                return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
        except AuthenticationFailed as exc:
            from django.http import JsonResponse
            return JsonResponse({"detail": str(exc)}, status=401)
        return super().dispatch(request, *args, **kwargs)

