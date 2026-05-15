"""
URL configuration for youpayroll project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from graphene_file_upload.django import FileUploadGraphQLView
from django.views.decorators.csrf import csrf_exempt
from youpayroll.schema import schema
from .views import HealthCheck


urlpatterns = [
    path('vinton-gray-cerf/', admin.site.urls),
    path('health/', HealthCheck.as_view(), name='health'),
    path('graphql/', FileUploadGraphQLView.as_view(graphiql=settings.DEBUG,
                                                               schema=schema)),
    path('accounts/', include('allauth.urls')),
    path('api/', include('core.urls')),
    path('api/payees/', include('payees.urls')),
    path('api/payroll/', include('payroll.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
