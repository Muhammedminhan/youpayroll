from rest_framework import serializers
from .models import Payee, BankDetails, BankDetailsAck

class BankDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = [
            'id', 'bank_name', 'account_no', 'account_holder_name',
            'account_type', 'ifsc_code', 'micr_code', 'swift_code',
            'branch_address', 'payee_acknowledgement'
        ]
        read_only_fields = ['payee_acknowledgement']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['account_no'] = instance.masked_account_no
        return ret

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        account_no = ret.get('account_no')
        if account_no and isinstance(account_no, str) and '*' in account_no:
            ret.pop('account_no')
        return ret

class PayeeSerializer(serializers.ModelSerializer):
    """General-purpose payee serializer. pan_no is excluded — use PayeePanSerializer for privileged PAN updates."""
    bank_details = BankDetailSerializer(source='bankdetails_set', many=True, read_only=True)

    class Meta:
        model = Payee
        fields = [
            'id', 'hrm_id', 'full_name', 'email',
            'date_of_joining', 'address', 'status', 'is_dark_mode',
            'bank_details'
        ]
        read_only_fields = ['id', 'hrm_id', 'status']


class PayeePanSerializer(serializers.ModelSerializer):
    """Privileged serializer for reading/updating pan_no. Reads return a masked value; writes accept a real PAN."""

    class Meta:
        model = Payee
        fields = ['id', 'pan_no']
        read_only_fields = ['id']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['pan_no'] = instance.masked_pan_no
        return ret

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        pan_no = ret.get('pan_no')
        if pan_no and isinstance(pan_no, str) and '*' in pan_no:
            ret.pop('pan_no')
        return ret

class BankDetailAcknowledgementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetailsAck
        fields = [
            'id', 'uploaded_date', 'bank_details_screenshot',
            'is_approved', 'correction_comments', 'bank_details'
        ]
        read_only_fields = ['uploaded_date', 'is_approved', 'correction_comments']

    def validate_bank_details(self, value):
        if BankDetailsAck.objects.filter(bank_details=value).exists():
            raise serializers.ValidationError("Bank details have already been acknowledged.")
        return value
