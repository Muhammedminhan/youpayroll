import graphene
from graphene_django.types import DjangoObjectType
from core.decorators import login_required
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
        acc = self.account_number
        if not acc:
            return ""
        if len(acc) <= 4:
            return "****"
        return f"****{acc[-4:]}"

    def resolve_ifsc_code(self, info):
        ifsc = self.ifsc_code or ""
        return "****" if ifsc else ""

    def resolve_micr_code(self, info):
        micr = self.micr_code or ""
        return "****" if micr else ""

    def resolve_swift_code(self, info):
        swift = self.swift_code or ""
        return "****" if swift else ""

    def resolve_branch_address(self, info):
        addr = self.branch_address or ""
        return "****" if addr else ""


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
