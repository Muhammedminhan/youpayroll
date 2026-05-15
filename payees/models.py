from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.db import models
from django.contrib.auth.models import User
from auditlog.registry import auditlog
from .upload_helpers import user_directory_path, validate_image
from .constants import (STATUS_CHOICES, PAYEE_STATUS_HELP_TEXT)
from configs.models import TDS

# Create your models here.


class Payee(models.Model):
    """ Stores the information of the Payee in the database """

    is_deleted = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='active',
                              help_text=PAYEE_STATUS_HELP_TEXT)
    hrm_id = models.CharField(max_length=10, help_text="Payee ID obtained "
                                                       "from Zoho people")
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
                help_text="Enable dark mode for a darker, "
                          "low-light-friendly interface ")

    class Meta:
        verbose_name = _("Payee")

    def __str__(self):
        if self.full_name is not None:
            return self.full_name
        return self.hrm_id

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()


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

    class Meta:
        verbose_name = _("Bank Detail")
        verbose_name_plural = _("Bank Details")

    def __str__(self):
        return self.account_holder_name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_state = {f.name: getattr(self, f.name) for f in self._meta.fields}

    def save(self, *args, **kwargs):
        if self.pk:
            tracked_fields = [
                'payee_id', 'bank_name', 'account_no', 'account_holder_name',
                'account_type', 'ifsc_code', 'micr_code', 'swift_code', 'branch_address'
            ]
            if any(getattr(self, f) != self._original_state.get(f) for f in tracked_fields):
                self.payee_acknowledgement = False
        super().save(*args, **kwargs)
        self._original_state = {f.name: getattr(self, f.name) for f in self._meta.fields}


auditlog.register(BankDetails)


class BankDetailsAck(models.Model):
    """ Stores the bank-acknowledgement file uploaded by the payee """

    payee = models.ForeignKey(Payee, on_delete=models.CASCADE,
                              related_name='bank_acknowledgement')
    uploaded_date = models.DateTimeField(auto_now_add=True)
    bank_details_screenshot = models.ImageField(
        upload_to=user_directory_path, validators=[validate_image,
                                                   FileExtensionValidator(
                                                       allowed_extensions=[
                                                           'jpg', 'jpeg',
                                                           'png'])])

    """Indicates the approval status of the bank details. True if the bank
    details are approved, False if rejected."""

    is_approved = models.BooleanField(default=False)
    correction_comments = models.TextField(blank=True, null=True,
                                           help_text="Please specify any "
                                                     "mistaken areas found "
                                                     "in the bank details.")

    class Meta:
        verbose_name = _("Bank Detail Acknowledgement")
        verbose_name_plural = _("Bank Detail Acknowledgements")

    def __str__(self):
        return self.payee.full_name or self.payee.hrm_id or str(self.pk)


auditlog.register(BankDetailsAck)
