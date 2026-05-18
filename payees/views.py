from rest_framework import viewsets, permissions, mixins
from rest_framework.exceptions import ValidationError
from .models import Payee, BankDetails, BankDetailsAck
from .serializers import PayeeSerializer, BankDetailSerializer, BankDetailAcknowledgementSerializer

class PayeeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PayeeSerializer
    queryset = Payee.objects.all().order_by('hrm_id')
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Payee.objects.all().order_by('hrm_id')
        return Payee.objects.filter(user=self.request.user).order_by('hrm_id')

class BankDetailViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BankDetailSerializer
    queryset = BankDetails.objects.all()
    
    def get_queryset(self):
        return BankDetails.objects.filter(payee__user=self.request.user)

    def perform_create(self, serializer):
        try:
            payee = Payee.objects.get(user=self.request.user)
        except Payee.DoesNotExist:
            raise ValidationError({"detail": "User is not registered as a payee."})
        serializer.save(payee=payee)

class BankDetailAcknowledgementViewSet(mixins.CreateModelMixin,
                                       mixins.ListModelMixin,
                                       mixins.RetrieveModelMixin,
                                       viewsets.GenericViewSet):
    """
    Acknowledgements are immutable user-attestations.
    Exposing only Create, List, and Retrieve.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BankDetailAcknowledgementSerializer
    queryset = BankDetailsAck.objects.all()
    
    def get_queryset(self):
        return BankDetailsAck.objects.filter(payee__user=self.request.user)

    def perform_create(self, serializer):
        try:
            payee = Payee.objects.get(user=self.request.user)
        except Payee.DoesNotExist:
            raise ValidationError({"detail": "User is not registered as a payee."})
        serializer.save(payee=payee)
