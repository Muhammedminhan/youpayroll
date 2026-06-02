from rest_framework import viewsets, permissions
from .models import PayRun, Payment, PayRecordRegister, Form16, Form16Entry
from .serializers import PayRunSerializer, PaymentSerializer, PayRecordRegisterSerializer, Form16Serializer, Form16EntrySerializer

# Authorization strategy per viewset:
#  - PayRunViewSet      : IsAdminUser — exposes all PayRuns to admins only (no per-user filtering).
#  - PaymentViewSet     : IsAuthenticated + get_queryset filters by request.user.
#  - PayRecordRegisterViewSet : IsAuthenticated + get_queryset filters by request.user.
#  - Form16ViewSet      : IsAdminUser — exposes all Form16 records to admins only (no per-user filtering).
#  - Form16EntryViewSet : IsAuthenticated + get_queryset filters by request.user.
#
# NOTE: All viewsets are ReadOnlyModelViewSet. If converting any to a standard ModelViewSet,
# you MUST implement robust object-level permissions (e.g. override check_object_permissions)
# to prevent unauthorized mutations.


class PayRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly monitoring of Payroll Runs for Admins.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = PayRunSerializer
    queryset = (
        PayRun.objects
        .prefetch_related('payrecordregister_set')
        .order_by('-created_at')
    )

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
        return (
            PayRecordRegister.objects
            .select_related('pay_run', 'payee')
            .filter(payee__user=self.request.user)
            .order_by('-record_created')
        )

class Form16ViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = Form16Serializer
    queryset = Form16.objects.all().order_by('-uploaded_on')

class Form16EntryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = Form16EntrySerializer
    queryset = Form16Entry.objects.none()

    def get_queryset(self):
        return (
            Form16Entry.objects
            .select_related('financial_year')
            .filter(payee__user=self.request.user)
        )
