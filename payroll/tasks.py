import logging

import datetime
import re
from celery import shared_task
from decimal import Decimal

from .models import (PayRun, Payment, PayRunStatusChoices, PayRecordRegister, Form16, Form16Entry)
from payees.models import Payee, BankDetails
import os
import zipfile
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q

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

    # Atomic state transition from DUE -> IN_PROGRESS to prevent concurrent worker race conditions
    updated_count = PayRun.objects.filter(id=payrun_id, status=PayRunStatusChoices.DUE).update(status=PayRunStatusChoices.IN_PROGRESS)
    
    if updated_count == 0:
        logger.warning('PayRun %s is not in DUE status or already being processed. Skipping.', payrun_id)
        return

    # Refresh object state
    pay_run.refresh_from_db()

    payees = Payee.objects.filter(status='active', is_deleted=False).select_related('tds_type')

    error_log = []

    try:
        for payee in payees:
            logger.info('Processing payee: %s', payee)
            # Each payee gets its own savepoint so a DB-level error (deadlock, constraint
            # violation) rolls back only that payee's record and leaves all previously
            # committed records intact.
            try:
                with transaction.atomic():
                    # Idempotency check: Skip if record already exists for this pay run
                    if PayRecordRegister.objects.filter(pay_run=pay_run, payee=payee).exists():
                        logger.info('PayRecordRegister already exists for payee: %s. Skipping.', payee.full_name)
                        continue

                    bank_details = BankDetails.objects.get(payee=payee, payee_acknowledgement=True)

                    # Determine the end of the pay run month
                    if pay_run.month == 12:
                        next_month = datetime.date(pay_run.year + 1, 1, 1)
                    else:
                        next_month = datetime.date(pay_run.year, pay_run.month + 1, 1)
                    end_of_month = next_month - datetime.timedelta(days=1)

                    month_start = datetime.date(pay_run.year, pay_run.month, 1)

                    # Sum all active payment rows for this pay run period.
                    # Multiple active Payment rows are summed rather than arbitrarily
                    # picking one (e.g. when a payee has both a base and an allowance row
                    # with the same effective_from date).
                    active_payments = Payment.objects.filter(
                        payee=payee,
                        effective_from__lte=end_of_month,
                    ).filter(
                        Q(effective_to__isnull=True) | Q(effective_to__gte=month_start)
                    )
                    if not active_payments.exists():
                        raise Payment.DoesNotExist

                    total_gross = sum(p.amount for p in active_payments)

                    tds_percentage = Decimal(str(payee.tds_type.tds_percentage if payee.tds_type else 0))
                    tds_amount = (Decimal(str(total_gross)) * tds_percentage) / Decimal('100')
                    total_net_income = Decimal(str(total_gross)) - tds_amount

                    PayRecordRegister.objects.create(
                        pay_run=pay_run,
                        amount=total_gross,
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
                        gross_amount=total_gross,
                        net_income=total_net_income,
                    )
                    logger.info('PayRecordRegister created for payee: %s', payee.full_name)

            except BankDetails.DoesNotExist:
                error_log.append(f"{payee.full_name} - Missing acknowledged bank details")
            except Payment.DoesNotExist:
                error_log.append(f"{payee.full_name} - No payment data available")
            except Exception as e:
                logger.error(f"Unexpected error for payee {payee}: {e}")
                error_log.append(f"{payee.full_name} - Unexpected error: {e}")

        # Status update committed in its own transaction so a previous DB error
        # during payee processing doesn't prevent the final status being saved.
        with transaction.atomic():
            pay_run.error_log = '\n'.join(error_log) if error_log else 'PayRecordRegister created successfully for every payee.'
            pay_run.status = PayRunStatusChoices.COMPLETED
            pay_run.save()
    except Exception as e:
        logger.error(f"Error in run_pay_run_task {payrun_id}: {e}")
        with transaction.atomic():
            pay_run.status = PayRunStatusChoices.REJECTED
            pay_run.error_log = f"Critical error during pay run: {e}"
            pay_run.save()

    logger.info('PayRun %s processing completed.', payrun_id)

@shared_task
def extract_form16_zip_task(form16_id):
    # select_for_update serialises concurrent retries: if two workers race, the
    # second acquires the lock after the first sets is_extracted=True and exits
    # early.  The lock is released as soon as the with block ends; the already-
    # loaded instance is used for the I/O work without holding any row lock.
    with transaction.atomic():
        try:
            instance = Form16.objects.select_for_update().get(pk=form16_id)
        except Form16.DoesNotExist:
            return
        if not instance.form16_zip_file or instance.is_extracted:
            return

    extracted_files = []
    skipped_files = []

    try:
        with instance.form16_zip_file.open('rb') as f:
            with zipfile.ZipFile(f, 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    if file_name.startswith("._") or "__MACOSX" in file_name:
                        continue

                    if file_name.lower().endswith(('.pdf', '.xml')):
                        cleaned_filename = os.path.basename(file_name)
                        if not cleaned_filename:
                            continue

                        save_path = f'uploads/payroll/form16/extracted/{cleaned_filename}'

                        if default_storage.exists(save_path):
                            default_storage.delete(save_path)

                        file_content = zip_ref.read(file_name)
                        if not file_content:
                            skipped_files.append(f"{file_name}: empty file")
                            continue

                        pan_no = cleaned_filename.split('_')[0].upper()
                        
                        # Validate PAN format (5 letters, 4 digits, 1 letter)
                        if not re.match(r'^[A-Z]{5}\d{4}[A-Z]$', pan_no):
                            logger.warning("Invalid PAN format '%s' derived from file %r. Skipping.", pan_no, cleaned_filename)
                            skipped_files.append(f"{file_name}: could not derive a valid PAN from filename")
                            continue

                        # Idempotency check: match exact basename to avoid false positives
                        # from __contains when two years share a filename. We match on the
                        # trailing path component (/<filename>) rather than any substring.
                        if Form16Entry.objects.filter(
                            financial_year=instance,
                            form_16__endswith=f'/{cleaned_filename}',
                        ).exists():
                            logger.info("Form 16 entry for %r already exists. Skipping.", cleaned_filename)
                            skipped_files.append(f"{file_name}: entry already exists")
                            continue

                        try:
                            pan_hash = Payee._hash_pan(pan_no)
                            payee = Payee.objects.get(pan_no_hash=pan_hash)
                        except Payee.DoesNotExist:
                            logger.warning("Payee with PAN %s not found for file %r. Skipping orphan creation.", pan_no, cleaned_filename)
                            skipped_files.append(f"{file_name}: no payee found for PAN {pan_no}")
                            continue

                        new_entry = Form16Entry(financial_year=instance, payee=payee)
                        new_entry.form_16.save(cleaned_filename, ContentFile(file_content), save=True)
                        extracted_files.append(file_name)

        instance.is_extracted = True
        if extracted_files or skipped_files:
            summary_parts = [f"Extracted {len(extracted_files)} file(s)."]
            if skipped_files:
                summary_parts.append("Skipped file(s):")
                summary_parts.extend(f"- {reason}" for reason in skipped_files)
            instance.extraction_summary = "\n".join(summary_parts)
        else:
            instance.extraction_summary = "No PDF or XML Form 16 files found in the ZIP archive."
        instance.save(update_fields=['is_extracted', 'extraction_summary'])
    except zipfile.BadZipFile:
        logger.error(f"Bad ZIP file encountered for Form16 ID {form16_id}")
