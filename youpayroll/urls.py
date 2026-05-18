"""
URL configuration for youpayroll project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from decouple import config
from graphene_file_upload.django import FileUploadGraphQLView
from youpayroll.schema import schema
from .views import LivenessCheck, ReadinessCheck, LegacyHealthCheck


urlpatterns = [
    # Admin URL
    path('admin/', admin.site.urls),
    
    # Modern Health Probes - Standardized with trailing slashes
    path('health/live/', LivenessCheck.as_view(), name='liveness_check'),
    path('health/ready/', ReadinessCheck.as_view(), name='readiness_check'),
    
    # Legacy Health Path (compatible with existing Helm/Ingress configs)
    path('health/', LegacyHealthCheck.as_view(), name='health_legacy'),
    
    # GraphQL - CSRF enforcement is handled via Authentication classes in settings
    path('graphql/', FileUploadGraphQLView.as_view(graphiql=config('ENABLE_GRAPHIQL', default=settings.DEBUG, cast=bool),
                                                                schema=schema)),
    path('accounts/', include('allauth.urls')),
    path('api/', include('core.urls')),
    path('api/payees/', include('payees.urls')),
    path('api/payroll/', include('payroll.urls')),
    path('api/configs/', include('configs.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
