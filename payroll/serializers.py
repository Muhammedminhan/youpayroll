from rest_framework import serializers
from .models import PayRun, Payment, PayRecordRegister, Form16, Form16Entry

class Form16EntrySerializer(serializers.ModelSerializer):
    financial_year_id = serializers.PrimaryKeyRelatedField(
        source='financial_year',
        read_only=True,
    )
    form16_financial_year = serializers.CharField(
        source='financial_year.financial_year',
        read_only=True,
    )

    class Meta:
        model = Form16Entry
        fields = ['id', 'financial_year_id', 'form16_financial_year', 'form_16']

class Form16Serializer(serializers.ModelSerializer):
    entries = Form16EntrySerializer(many=True, read_only=True)
    class Meta:
        model = Form16
        fields = ['id', 'financial_year', 'uploaded_on', 'form16_zip_file', 'is_extracted', 'extraction_summary', 'entries']
        read_only_fields = ['uploaded_on', 'is_extracted', 'extraction_summary']

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
    account_number = serializers.SerializerMethodField()
    ifsc_code = serializers.SerializerMethodField()
    micr_code = serializers.SerializerMethodField()
    swift_code = serializers.SerializerMethodField()
    branch_address = serializers.SerializerMethodField()

    class Meta:
        model = PayRecordRegister
        fields = [
            'id', 'record_created', 'pay_run', 'amount', 'payee',
            'bank_name', 'account_number', 'account_holder_name',
            'account_type', 'ifsc_code', 'micr_code', 'swift_code',
            'branch_address', 'tds_percentage', 'gross_amount', 'net_income'
        ]
        # Make all fields read-only
        read_only_fields = fields

    def get_account_number(self, obj):
        acc = obj.account_number
        if not acc:
            return ""
        if len(acc) <= 4:
            return "****"
        return f"****{acc[-4:]}"

    def get_ifsc_code(self, obj):
        ifsc = obj.ifsc_code or ""
        return "****" if ifsc else ""

    def get_micr_code(self, obj):
        micr = obj.micr_code or ""
        return "****" if micr else ""

    def get_swift_code(self, obj):
        swift = obj.swift_code or ""
        return "****" if swift else ""

    def get_branch_address(self, obj):
        addr = obj.branch_address or ""
        return "****" if addr else ""
