import base64
import binascii
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Payslip, Document, AdminNotification, WikiCategory, WikiPage, UserNotification

class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = ['id', 'user', 'title', 'message', 'notification_type', 'is_read', 'created_at']

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            # The declared MIME type from the data URI is client-controlled and
            # cannot be trusted on its own. Decode first, then verify content
            # via PIL (same check used by validate_image in upload_helpers.py).
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            header_end = data.find(';')
            if header_end == -1:
                raise serializers.ValidationError("Invalid data URI format.")

            mime_type = data[5:header_end]
            if mime_type not in allowed_types:
                raise serializers.ValidationError(f"Unsupported image type: {mime_type}. Use JPG or PNG.")

            try:
                header, imgstr = data.split(';base64,')
                ext = header.split('/')[-1]
                file_name = f"{uuid.uuid4().hex[:10]}.{ext}"
                decoded = base64.b64decode(imgstr)
                data = ContentFile(decoded, name=file_name)
            except (ValueError, binascii.Error):
                raise serializers.ValidationError("Invalid image format. Please ensure the base64 string is valid.")

            # PIL content-based verification — rejects files whose bytes don't
            # match the declared image type regardless of header claims.
            try:
                from PIL import Image, UnidentifiedImageError
                import io
                with Image.open(io.BytesIO(decoded)) as img:
                    img.verify()
            except Exception:
                raise serializers.ValidationError("Invalid image content. The file could not be read as an image.")

        return super().to_internal_value(data)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    profile_picture = Base64ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Profile
        fields = [
            'id', 'user', 'first_name', 'last_name', 'profile_picture',
            'gender', 'dob', 'designation'
        ]
        read_only_fields = ['id', 'user']

    def update(self, instance, validated_data):
        # Extract name data
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        
        user = instance.user
        update_fields = []
        if first_name is not None:
            user.first_name = first_name
            update_fields.append('first_name')
        if last_name is not None:
            user.last_name = last_name
            update_fields.append('last_name')
        if update_fields:
            user.save(update_fields=update_fields)
            
        # Explicitly handle profile_picture deletion/update
        if 'profile_picture' in validated_data:
            pic_data = validated_data.get('profile_picture')
            if pic_data is None:
                if instance.profile_picture:
                    instance.profile_picture.delete(save=False)
                instance.profile_picture = None
            else:
                instance.profile_picture = pic_data
            
        return super().update(instance, validated_data)

class PayslipSerializer(serializers.ModelSerializer):
    consultant_id = serializers.SerializerMethodField()
    account_number = serializers.SerializerMethodField()
    ifsc_code = serializers.SerializerMethodField()
    branch_address = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = [
            'id', 'user', 'month', 'year', 'gross_pay', 'reimbursement',
            'deductions', 'take_home', 'file', 'tax_worksheet', 'created_at',
            'consultant_id', 'account_number', 'ifsc_code', 'branch_address'
        ]

    def to_representation(self, instance):
        # Fetch BankDetails once per payslip and stash it on the instance so the
        # three SerializerMethodFields below share the same result without issuing
        # three identical queries (24 payslips × 3 fields = 72 extra queries avoided).
        from payees.models import BankDetails
        if not hasattr(instance, '_cached_bank_detail'):
            instance._cached_bank_detail = BankDetails.objects.filter(
                payee__user=instance.user
            ).first()
        return super().to_representation(instance)

    def _bank_detail(self, obj):
        if not hasattr(obj, '_cached_bank_detail'):
            from payees.models import BankDetails
            obj._cached_bank_detail = BankDetails.objects.filter(payee__user=obj.user).first()
        return obj._cached_bank_detail

    def get_consultant_id(self, obj):
        return getattr(obj.user.profile, 'consultant_id', '') if hasattr(obj.user, 'profile') else ''

    def get_account_number(self, obj):
        bank_detail = self._bank_detail(obj)
        return bank_detail.masked_account_no if bank_detail else ''

    def get_ifsc_code(self, obj):
        bank_detail = self._bank_detail(obj)
        if not bank_detail or not bank_detail.ifsc_code:
            return ''
        code = bank_detail.ifsc_code
        return f"{'*' * (len(code) - 4)}{code[-4:]}" if len(code) > 4 else '****'

    def get_branch_address(self, obj):
        bank_detail = self._bank_detail(obj)
        if not bank_detail or not bank_detail.branch_address:
            return ''
        return '****'


class BankDetailsSerializer(serializers.ModelSerializer):
    """Serializer for the canonical payees.BankDetails model.
    Read path returns masked account number; write path accepts plain text
    (masking is display-only).
    """
    from payees.models import BankDetails
    account_no = serializers.CharField(read_only=True, source='masked_account_no')
    account_no_plain = serializers.CharField(write_only=True, required=False, source='account_no')

    class Meta:
        from payees.models import BankDetails
        model = BankDetails
        fields = [
            'id', 'bank_name', 'account_no', 'account_no_plain',
            'account_holder_name', 'account_type',
            'ifsc_code', 'micr_code', 'swift_code', 'branch_address',
            'payee_acknowledgement',
        ]
        read_only_fields = ['id', 'payee_acknowledgement']

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'user', 'title', 'description', 'status', 'file', 'admin_feedback', 'updated_at']
        read_only_fields = ['user', 'status', 'admin_feedback', 'updated_at']

class AdminNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminNotification
        fields = ['id', 'title', 'message', 'is_active', 'created_at']

class WikiCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WikiCategory
        fields = ['id', 'name', 'slug', 'description', 'created_at']

class WikiPageSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = WikiPage
        fields = [
            'id', 'title', 'slug', 'content', 'category', 'category_name',
            'author', 'author_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'slug']
