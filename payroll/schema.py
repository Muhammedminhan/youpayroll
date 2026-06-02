import graphene
from graphene_django.types import DjangoObjectType
from core.decorators import login_required
from payees.utils_masking import mask_if_present, mask_last_four
from .models import Payment, PayRecordRegister


class PayRecordRegisterType(DjangoObjectType):
    """
    This section displays the payee's bank information, along with the
    salary and TDS percentage.
    """
    class Meta:
        model = PayRecordRegister
        fields = ('amount', 'bank_name', 'payee', 'account_number',
                  'account_holder_name', 'account_type', 'ifsc_code',
                  'micr_code', 'swift_code', 'branch_address',
                  'tds_percentage', 'gross_amount')

    def resolve_account_number(self, info):
        return mask_last_four(self.account_number)

    def resolve_ifsc_code(self, info):
        return mask_if_present(self.ifsc_code)

    def resolve_micr_code(self, info):
        return mask_if_present(self.micr_code)

    def resolve_swift_code(self, info):
        return mask_if_present(self.swift_code)

    def resolve_branch_address(self, info):
        return mask_if_present(self.branch_address)


class PaymentType(DjangoObjectType):
    """
    This section displays the salary amount of the employee
    """
    class Meta:
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
