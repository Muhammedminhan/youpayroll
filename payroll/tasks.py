import logging

from celery import shared_task
from decimal import Decimal

from .models import (PayRun, Payment, PayRunStatusChoices, PayRecordRegister, Form16, Form16Entries)
from payees.models import Payee, BankDetails
import os
import zipfile
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

# For getting the named logger
logger = logging.getLogger('celery_debug')


@shared_task
def run_pay_run_task(payrun_id):
    logger.info('Starting task with pay_run_id: %s', payrun_id)

    try:
        pay_run = PayRun.objects.get(id=payrun_id)
    except PayRun.DoesNotExist:
        logger.error('PayRun with ID %s does not exist.', payrun_id)
        return

    if pay_run.status != PayRunStatusChoices.DUE:
        logger.warning('PayRun %s is not in DUE status. Skipping.', payrun_id)
        return

    payees = Payee.objects.filter(status='active', is_deleted=False)
    pay_run.status = PayRunStatusChoices.IN_PROGRESS
    pay_run.save()

    error_log = []

    for payee in payees:
        logger.info('Processing payee: %s', payee)

        try:
            bank_details = BankDetails.objects.get(payee=payee, payee_acknowledgement=True)
        except BankDetails.DoesNotExist:
            error_log.append(f"{payee.full_name} - Missing acknowledged bank "
                             f"details")
            continue

        try:
            total_amount = Payment.objects.get(payee=payee)
        except Payment.DoesNotExist:
            error_log.append(f"{payee.full_name} - No payment data available")
            continue

        tds_percentage = Decimal(str(payee.tds_type.tds_percentage if payee.tds_type else 0))
        tds_amount = (total_amount.amount * tds_percentage) / Decimal('100')
        total_net_income = total_amount.amount - tds_amount

        PayRecordRegister.objects.create(
            pay_run=pay_run,
            amount=total_amount.amount,
            payee=payee,
            bank_name=bank_details.bank_name,
            account_number=bank_details.account_no,
            account_holder_name=bank_details.account_holder_name,
            account_type=bank_details.account_type,
            ifsc_code=bank_details.ifsc_code,
            micr_code=bank_details.micr_code,
            swift_code=bank_details.swift_code,
            branch_address=bank_details.branch_address,
            tds_percentage=tds_percentage,
            gross_amount=total_amount.amount,
            net_income=total_net_income,
        )
        logger.info('PayRecordRegister created for payee: %s',payee.full_name )

    if error_log:
        pay_run.error_log = '\n'.join(error_log)
    else:
        pay_run.error_log = 'PayRecordRegister created successfully for every payee.'

    pay_run.status = PayRunStatusChoices.COMPLETED
    pay_run.save()

    logger.info('PayRun %s processing completed.', payrun_id)

@shared_task
def extract_form16_zip_task(form16_id):
    try:
        instance = Form16.objects.get(pk=form16_id)
    except Form16.DoesNotExist:
        return

    if not instance.form16_zip_file or instance.is_extracted:
        return

    try:
        with zipfile.ZipFile(instance.form16_zip_file.open('rb')) as zip_ref:
            for file_name in zip_ref.namelist():
                if file_name.startswith("._") or "__MACOSX" in file_name:
                    continue

                if file_name.lower().endswith(('.pdf', '.xml')):
                    cleaned_filename = os.path.basename(file_name)
                    save_path = f'uploads/payroll/form16/extracted/{cleaned_filename}'

                    if default_storage.exists(save_path):
                        default_storage.delete(save_path)

                    file_content = zip_ref.read(file_name)
                    if not file_content:
                        continue

                    pan_no = cleaned_filename.split('_')[0].upper()
                    try:
                        payee = Payee.objects.get(pan_no=pan_no)
                    except Payee.DoesNotExist:
                        payee = None

                    new_entry = Form16Entries(financial_year=instance, payee=payee)
                    new_entry.form_16.save(cleaned_filename, ContentFile(file_content), save=True)

        instance.is_extracted = True
        instance.save(update_fields=['is_extracted'])
    except zipfile.BadZipFile:
        logger.error(f"Bad ZIP file encountered for Form16 ID {form16_id}")


