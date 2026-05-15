from rest_framework import viewsets, permissions
from .models import PayRun, Payment, PayRecordRegister, Form16, Form16Entries
from .serializers import PayRunSerializer, PaymentSerializer, PayRecordRegisterSerializer, Form16Serializer, Form16EntrySerializer

class PayRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly monitoring of Payroll Runs for Admins.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = PayRunSerializer
    queryset = PayRun.objects.all().order_by('-created_at')

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer
    # Model specified for DRF router introspection
    queryset = Payment.objects.none()
    
    def get_queryset(self):
        return Payment.objects.filter(payee__user=self.request.user).order_by('-id')

class PayRecordRegisterViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PayRecordRegisterSerializer
    queryset = PayRecordRegister.objects.none()

    def get_queryset(self):
        return PayRecordRegister.objects.filter(payee__user=self.request.user).order_by('-record_created')

class Form16ViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = Form16Serializer
    queryset = Form16.objects.all().order_by('-uploaded_on')

class Form16EntryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = Form16EntrySerializer
    queryset = Form16Entries.objects.none()

    def get_queryset(self):
        return Form16Entries.objects.filter(payee__user=self.request.user)
