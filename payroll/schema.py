import graphene
from graphene_django.types import DjangoObjectType
from core.decorators import login_required
from .models import Payment, PayRecordRegister


class PayRecordRegisterType(DjangoObjectType):
    class Meta:
        """
        This section displays the payee's bank information, along with the
        salary and TDS percentage.
        """
        model = PayRecordRegister
        fields = ('amount', 'bank_name', 'payee', 'account_number',
                  'account_holder_name', 'account_type', 'ifsc_code',
                  'micr_code', 'swift_code', 'branch_address',
                  'tds_percentage', 'gross_amount')


class PaymentType(DjangoObjectType):
    class Meta:
        """
        This section displays the salary amount of the employee
        """
        model = Payment
        fields = ('amount', 'label', 'payee')


class PayrollQuery(graphene.ObjectType):
    all_payments = graphene.List(PaymentType)
    all_pay_record_register = graphene.List(PayRecordRegisterType)

    @staticmethod
    @login_required
    def resolve_all_payments(root, info):
        return Payment.objects.filter(payee__user=info.context.user)

    @staticmethod
    @login_required
    def resolve_all_pay_record_register(root, info):
        return PayRecordRegister.objects.filter(payee__user=info.context.user)
