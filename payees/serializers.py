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
        read_only_fields = ['payee', 'payee_acknowledgement']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        acc = instance.account_no or ""
        if acc:
            ret['account_no'] = "**********"
        else:
            ret['account_no'] = ""
        return ret

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        if 'account_no' in ret and ret['account_no'] == '**********':
            ret.pop('account_no')
        return ret

class PayeeSerializer(serializers.ModelSerializer):
    bank_details = BankDetailSerializer(source='bankdetails_set', many=True, read_only=True)
    class Meta:
        model = Payee
        fields = [
            'id', 'hrm_id', 'full_name', 'email', 'pan_no', 
            'date_of_joining', 'address', 'status', 'is_dark_mode',
            'bank_details'
        ]
        read_only_fields = ['id', 'hrm_id', 'status']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        pan = instance.pan_no or ""
        if pan:
            ret['pan_no'] = "**********"
        else:
            ret['pan_no'] = ""
        return ret

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        if 'pan_no' in ret and ret['pan_no'] == '**********':
            ret.pop('pan_no')
        return ret

class BankDetailAcknowledgementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetailsAck
        fields = [
            'id', 'uploaded_date', 'bank_details_screenshot',
            'is_approved', 'correction_comments'
        ]
        read_only_fields = ['payee', 'uploaded_date', 'is_approved', 'correction_comments']
