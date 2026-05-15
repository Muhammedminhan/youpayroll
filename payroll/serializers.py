from rest_framework import serializers
from .models import PayRun, Payment, PayRecordRegister, Form16, Form16Entries

class Form16EntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Form16Entries
        fields = '__all__'

class Form16Serializer(serializers.ModelSerializer):
    entries = Form16EntrySerializer(many=True, read_only=True)
    class Meta:
        model = Form16
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class PayRunSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    class Meta:
        model = PayRun
        fields = '__all__'

class PayRecordRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayRecordRegister
        fields = '__all__'
