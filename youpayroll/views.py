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
        except Exception as e:
            logger.error(f"Readiness check failed: {str(e)}")
            return HttpResponse("Service Unavailable", status=503)

class LegacyHealthCheck(LivenessCheck):
    """
    Temporary compatibility endpoint for /health/ which is used by ALB
    and K8s liveness probes. Inherits from LivenessCheck to avoid 
    killing pods on transient DB blips.
    """
    pass
