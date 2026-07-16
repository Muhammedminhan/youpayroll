from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator, FileExtensionValidator
from django.db import models, transaction
from safedelete import SOFT_DELETE
from safedelete.models import SafeDeleteModel
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from auditlog.registry import auditlog
import hashlib
import hmac
from django.conf import settings
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField
from .upload_helpers import user_directory_path, validate_image
from .constants import (STATUS_CHOICES, PAYEE_STATUS_HELP_TEXT)
from configs.models import TDS

class Payee(SafeDeleteModel):
    """ Stores the information of the Payee in the database """
    _safedelete_policy = SOFT_DELETE
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='active',
                              help_text=PAYEE_STATUS_HELP_TEXT)
    hrm_id = models.CharField(max_length=10, unique=True, help_text="Payee ID obtained from Zoho people")
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    tds_type = models.ForeignKey(TDS, on_delete=models.SET_NULL, blank=True,
                                 null=True)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    pan_no = EncryptedCharField(max_length=10, null=True, blank=True)
    # HMAC-SHA256 of pan_no used to enforce uniqueness without storing plaintext.
    # EncryptedCharField is non-deterministic so DB unique=True on it is unreliable.
    pan_no_hash = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    date_of_joining = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    is_dark_mode = models.BooleanField(default=False,
                help_text="Enable dark mode for a low-light-friendly interface.")

    class Meta:
        verbose_name = _("Payee")

    @property
    def masked_pan_no(self):
        return "**********" if self.pan_no else ""

    @staticmethod
    def _hash_pan(pan_no):
        key = (getattr(settings, 'PAN_HASH_KEY', None) or settings.SECRET_KEY).encode()
        return hmac.new(key, pan_no.upper().encode(), hashlib.sha256).hexdigest()

    def save(self, *args, **kwargs):
        self.pan_no_hash = self._hash_pan(self.pan_no) if self.pan_no else None
        with transaction.atomic():
            if self.user_id and self.email:
                EmailValidator()(self.email)
                User.objects.filter(pk=self.user_id).exclude(email=self.email).update(email=self.email)
            elif self.user_id and not self.email:
                self.email = self.user.email
            super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.hrm_id

auditlog.register(Payee)


@receiver(post_save, sender=User)
def sync_payee_email_from_user(sender, instance, **kwargs):
    if instance.email:
        Payee.objects.filter(user=instance).exclude(email=instance.email).update(email=instance.email)

class BankDetails(models.Model):
    """ Stores the information of the Payee Bank Account details """
    payee = models.ForeignKey(Payee, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_no = EncryptedCharField(max_length=100, null=True, blank=True)
    account_holder_name = models.CharField(max_length=100, null=True,
                                           blank=True)
    account_type = models.CharField(max_length=10, null=True, blank=True)
    ifsc_code = EncryptedCharField(max_length=100, null=True, blank=True)
    micr_code = EncryptedCharField(max_length=100, null=True, blank=True)
    swift_code = EncryptedCharField(max_length=100, null=True, blank=True)
    branch_address = EncryptedTextField(null=True, blank=True)
    payee_acknowledgement = models.BooleanField(default=False, editable=False)

    @property
    def masked_account_no(self):
        acc = self.account_no or ""
        if acc and len(acc) > 4:
            return f"{'*' * (len(acc) - 4)}{acc[-4:]}"
        return "**********" if acc else ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set_state_snapshot()

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._set_state_snapshot()
        return instance

    def _set_state_snapshot(self):
        # Snapshot state for mutation tracking
        self._original_state = {
            'bank_name': self.bank_name,
            'account_no': self.account_no,
            'account_holder_name': self.account_holder_name,
            'account_type': self.account_type,
            'ifsc_code': self.ifsc_code,
            'micr_code': self.micr_code,
            'swift_code': self.swift_code,
            'branch_address': self.branch_address,
        }

    class Meta:
        verbose_name = _("Bank Detail")
        verbose_name_plural = _("Bank Details")
        constraints = [
            models.UniqueConstraint(
                fields=['payee'],
                name='unique_bank_details_per_payee',
            ),
        ]

    def save(self, *args, **kwargs):
        # Reset acknowledgement if tracked fields changed
        original_state = getattr(self, '_original_state', {})
        tracked_fields = original_state.keys()
        changed_fields = [f for f in tracked_fields if getattr(self, f) != original_state.get(f)]
        
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            # Only reset if a tracked field being updated has actually changed in memory
            effective_changes = [f for f in changed_fields if f in update_fields]
        else:
            effective_changes = changed_fields

        with transaction.atomic():
            if effective_changes:
                if self.pk:
                    # Old acknowledgement screenshots attest to the prior bank details.
                    # Deleting them invalidates that attestation; auditlog records the deletion.
                    self.acknowledgements.all().delete()
                self.payee_acknowledgement = False
                if update_fields is not None and 'payee_acknowledgement' not in update_fields:
                    kwargs['update_fields'] = list(update_fields) + ['payee_acknowledgement']

            super().save(*args, **kwargs)
        self._set_state_snapshot() # Refresh snapshot after save

    def __str__(self):
        return self.account_holder_name or f"BankDetails {self.pk}"

auditlog.register(BankDetails)

class BankDetailsAck(models.Model):
    """ Stores the bank-acknowledgement file uploaded by the payee """
    payee = models.ForeignKey(Payee, on_delete=models.CASCADE,
                              related_name='bank_acknowledgement')
    # Link to the specific bank record being acknowledged to avoid race/ambiguity
    bank_details = models.ForeignKey(BankDetails, on_delete=models.CASCADE,
                                     related_name='acknowledgements')
    uploaded_date = models.DateTimeField(auto_now_add=True)
    bank_details_screenshot = models.ImageField(
        upload_to=user_directory_path, validators=[validate_image,
                                                   FileExtensionValidator(
                                                       allowed_extensions=[
                                                           'jpg', 'jpeg',
                                                           'png'])])
    is_approved = models.BooleanField(default=False)
    correction_comments = models.TextField(blank=True, null=True,
                                           help_text="Specify any incorrect or mistaken fields in the bank details.")

    class Meta:
        verbose_name = _("Bank Detail Acknowledgement")
        verbose_name_plural = _("Bank Detail Acknowledgements")
        constraints = [
            models.UniqueConstraint(
                fields=['bank_details'],
                name='unique_ack_per_bank_details',
            ),
        ]

    def __str__(self):
        return self.payee.full_name or self.payee.hrm_id or str(self.pk)

auditlog.register(BankDetailsAck)
