from rest_framework import serializers
from .models import PayRun, Payment, PayRecordRegister, Form16, Form16Entries

class Form16EntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Form16Entries
        fields = ['id', 'financial_year', 'form_16']
        read_only_fields = ['id', 'financial_year', 'form_16']

class Form16Serializer(serializers.ModelSerializer):
    entries = Form16EntrySerializer(source='form16entries_set', many=True, read_only=True)
    class Meta:
        model = Form16
        fields = ['id', 'financial_year', 'uploaded_on', 'form16_zip_file', 'is_extracted', 'entries']
        read_only_fields = ['uploaded_on', 'is_extracted']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'amount', 'label']
        read_only_fields = ['id']

class PayRunSerializer(serializers.ModelSerializer):
    # Fixed reverse relation to records
    records = serializers.PrimaryKeyRelatedField(source='payrecordregister_set', many=True, read_only=True)
    class Meta:
        model = PayRun
        fields = ['id', 'month', 'year', 'status', 'created_at', 'error_log', 'records']
        read_only_fields = ['created_at', 'error_log']

class PayRecordRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayRecordRegister
        fields = [
            'id', 'record_created', 'pay_run', 'amount', 'payee',
            'bank_name', 'account_number', 'account_holder_name',
            'account_type', 'ifsc_code', 'micr_code', 'swift_code',
            'branch_address', 'tds_percentage', 'gross_amount', 'net_income'
        ]
        read_only_fields = fields 
