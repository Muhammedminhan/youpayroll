from rest_framework import serializers
from .models import Payee, BankDetails, BankDetailsAck

class BankDetailSerializer(serializers.ModelSerializer):
    account_no = serializers.SerializerMethodField()

    class Meta:
        model = BankDetails
        fields = [
            'id', 'bank_name', 'account_no', 'account_holder_name',
            'account_type', 'ifsc_code', 'micr_code', 'swift_code',
            'branch_address', 'payee_acknowledgement'
        ]
        read_only_fields = ['payee', 'payee_acknowledgement']

    def get_account_no(self, obj):
        # Mask account number: fixed width plus last 4
        acc = obj.account_no or ""
        if len(acc) <= 4:
            return "****"
        return f"****{acc[-4:]}"

class PayeeSerializer(serializers.ModelSerializer):
    pan_no = serializers.SerializerMethodField()
    bank_details = BankDetailSerializer(source='bankdetails_set', many=True, read_only=True)
    class Meta:
        model = Payee
        fields = [
            'id', 'hrm_id', 'full_name', 'email', 'pan_no', 
            'date_of_joining', 'address', 'status', 'is_dark_mode',
            'bank_details'
        ]
        read_only_fields = ['id', 'hrm_id', 'status']

    def get_pan_no(self, obj):
        # Mask PAN: fixed width masking to avoid length/pattern leaks
        pan = obj.pan_no or ""
        if not pan:
            return ""
        return "**********"

class BankDetailAcknowledgementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetailsAck
        fields = [
            'id', 'uploaded_date', 'bank_details_screenshot',
            'is_approved', 'correction_comments'
        ]
        read_only_fields = ['payee', 'uploaded_date', 'is_approved', 'correction_comments']
