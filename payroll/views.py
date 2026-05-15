from rest_framework import viewsets, permissions, mixins
from .models import PayRun, Payment, PayRecordRegister, Form16, Form16Entries
from .serializers import PayRunSerializer, PaymentSerializer, PayRecordRegisterSerializer, Form16Serializer, Form16EntrySerializer

class PayRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    PayRuns are created via backend processes.
    Exposing as ReadOnly for Admins to monitor.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = PayRunSerializer
    queryset = PayRun.objects.all()

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer
    # Explicit none() for safety
    queryset = Payment.objects.none()
    
    def get_queryset(self):
        return Payment.objects.filter(payee__user=self.request.user)

class PayRecordRegisterViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PayRecordRegisterSerializer
    queryset = PayRecordRegister.objects.none()

    def get_queryset(self):
        return PayRecordRegister.objects.filter(payee__user=self.request.user)

class Form16ViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = Form16Serializer
    queryset = Form16.objects.all()

class Form16EntryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = Form16EntrySerializer
    queryset = Form16Entries.objects.none()

    def get_queryset(self):
        return Form16Entries.objects.filter(payee__user=self.request.user)
