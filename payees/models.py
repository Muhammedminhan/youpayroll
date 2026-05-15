from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from safedelete.models import SafeDeleteModel
from django.contrib.auth.models import User
from auditlog.registry import auditlog
from .upload_helpers import user_directory_path, validate_image
from .constants import (STATUS_CHOICES, PAYEE_STATUS_HELP_TEXT)
from configs.models import TDS

class Payee(SafeDeleteModel):
    """ Stores the information of the Payee in the database """
    _safedelete_policy = 1
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='active',
                              help_text=PAYEE_STATUS_HELP_TEXT)
    hrm_id = models.CharField(max_length=10, unique=True, help_text="Payee ID obtained from Zoho people")
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    tds_type = models.ForeignKey(TDS, on_delete=models.SET_NULL, blank=True,
                                 null=True)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    pan_no = models.CharField(max_length=10, unique=True, null=True,
                               blank=True)
    date_of_joining = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    is_dark_mode = models.BooleanField(default=False,
                help_text="Enable dark mode for a low-light-friendly interface.")

    class Meta:
        verbose_name = _("Payee")

    def __str__(self):
        return self.full_name or self.hrm_id

auditlog.register(Payee)

class BankDetails(models.Model):
    """ Stores the information of the Payee Bank Account details """
    payee = models.ForeignKey(Payee, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_no = models.CharField(max_length=100, null=True, blank=True)
    account_holder_name = models.CharField(max_length=100, null=True,
                                           blank=True)
    account_type = models.CharField(max_length=10, null=True, blank=True)
    ifsc_code = models.CharField(max_length=100, null=True, blank=True)
    micr_code = models.CharField(max_length=100, null=True, blank=True)
    swift_code = models.CharField(max_length=100, null=True, blank=True)
    branch_address = models.TextField(null=True, blank=True)
    payee_acknowledgement = models.BooleanField(default=False, editable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set_state_snapshot()

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

    def save(self, *args, **kwargs):
        # Reset acknowledgement if tracked fields changed
        tracked_fields = self._original_state.keys()
        if any(getattr(self, f) != self._original_state[f] for f in tracked_fields):
            self.payee_acknowledgement = False
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
                                     related_name='acknowledgements', null=True)
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

    def __str__(self):
        return self.payee.full_name or self.payee.hrm_id or str(self.pk)

auditlog.register(BankDetailsAck)
