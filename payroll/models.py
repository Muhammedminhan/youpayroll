import os
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from auditlog.registry import auditlog
from .utils import get_month_name
from payees.models import Payee
from configs.models import Component
from .upload_helpers import (validate_zip_file,
                             form16_extracted_path)


# Create your models here.

class Payment(models.Model):
    """ Stores the information of the Payee salary details """

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    label = models.CharField(max_length=50)
    payee = models.OneToOneField(Payee, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")

    def __str__(self):
        return self.label


auditlog.register(Payment)


class PayRunStatusChoices(models.TextChoices):
    DUE = 'due', _('DUE')
    IN_PROGRESS = 'in_progress', _('IN PROGRESS')
    COMPLETED = 'completed', _('COMPLETED')
    REJECTED = 'rejected', _('REJECTED')
    APPROVED = 'approved', _('APPROVED')


class PayRun(models.Model):
    """
    This model keeps track of payment details for each month before
    processing payments.
    Payments are only made to payees who are active and have
    acknowledged their bank details.
    """
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.IntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    status = models.CharField(max_length=20,
                              choices=PayRunStatusChoices.choices,
                              default=PayRunStatusChoices.DUE)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   editable=False, null=True, blank=True)
    error_log = models.TextField(blank=True, null=True,
                                 help_text="Shows only if any errors occur "
                                           "in payees data.")

    class Meta:
        verbose_name = _("Pay Run")
        verbose_name_plural = _("Pay Runs")
        unique_together = (('month', 'year'),)

    def get_error_log_lines(self):
        return self.error_log.splitlines() if self.error_log else []

    def display_month_name(self):
        return get_month_name(self.month)

    def __str__(self):
        return (f"{self.display_month_name()} {self.year} - "
                f"{self.get_status_display()}")


auditlog.register(PayRun)


class PayRecordRegister(models.Model):
    """ Stores the details of amount paid to each tds type and their account
    details after each successful Pay run """

    record_created = models.DateTimeField(auto_now_add=True)
    pay_run = models.ForeignKey(PayRun, on_delete=models.CASCADE, null=True,
                                blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                                 blank=True)
    payee = models.ForeignKey(Payee, on_delete=models.CASCADE)

    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(null=True, blank=True, max_length=16)
    account_holder_name = models.CharField(max_length=100, null=True,
                                           blank=True)
    account_type = models.CharField(max_length=10, null=True, blank=True)
    ifsc_code = models.CharField(max_length=100, null=True, blank=True)
    micr_code = models.CharField(max_length=100, null=True, blank=True)
    swift_code = models.CharField(max_length=100, null=True, blank=True)
    branch_address = models.TextField(null=True, blank=True)
    tds_percentage = models.FloatField(null=True, blank=True)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2,
                                       null=True, blank=True)
    net_income = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('payee', 'pay_run')
        ordering = ['-record_created']
        verbose_name = _("Pay Record Register")
        verbose_name_plural = _("Pay Record Registers")

    def __str__(self):
        return f"{self.payee.full_name} | {self.pay_run}"


auditlog.register(PayRecordRegister)


class ComponentValue(models.Model):
    pay_record = models.ForeignKey(PayRecordRegister, on_delete=models.CASCADE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return ""


auditlog.register(ComponentValue)


class Form16(models.Model):
    financial_year = models.CharField(max_length=10, null=True, blank=True)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    form16_zip_file = models.FileField(upload_to='uploads/payroll/form16/',
                                       validators=[validate_zip_file])
    is_extracted = models.BooleanField(default=False)

    def __str__(self):
        return self.financial_year


auditlog.register(Form16)


class Form16Entry(models.Model):
    financial_year = models.ForeignKey(Form16, on_delete=models.CASCADE, related_name='entries')
    payee = models.ForeignKey(Payee, on_delete=models.SET_NULL, null=True,
                              blank=True)
    form_16 = models.FileField(upload_to=form16_extracted_path)

    def __str__(self):
        return os.path.basename(self.form_16.name)

    class Meta:
        verbose_name = "Form 16 Entry"
        verbose_name_plural = "Form 16 Entries"


auditlog.register(Form16Entry)
