from rest_framework import viewsets, permissions
from .models import Component, TDS
from .serializers import ComponentSerializer, TaxDeductedAtSourceSerializer

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin/staff users to edit/delete objects.
    General authenticated users can only read.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and (request.user.is_staff or request.user.is_superuser)

class ComponentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = ComponentSerializer
    queryset = Component.objects.all()

class TaxDeductedAtSourceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = TaxDeductedAtSourceSerializer
    queryset = TDS.objects.all()
