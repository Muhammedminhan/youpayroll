from django.contrib import messages

from .models import PayRunStatusChoices, Payee
from .tasks import run_pay_run_task
from .utils import (check_single_payrun_selection, check_latest_payrun,
                    get_latest_payrun)


def approve_payrun_action(modeladmin, request, queryset):
    """
    Approve the selected payrun entry.
    """
    # Retrieves the first PayRun from the queryset or None if empty.
    selected_payrun = queryset.first()

    # Retrieves the most recent PayRun or None if none exist.
    latest_payrun = get_latest_payrun()

    if check_single_payrun_selection(queryset, modeladmin, request) == False:
        return

    if check_latest_payrun(modeladmin, request, selected_payrun,
                           latest_payrun) == False:
        return

    if latest_payrun.status == PayRunStatusChoices.COMPLETED:
        latest_payrun.status = PayRunStatusChoices.APPROVED
        latest_payrun.save()
        modeladmin.message_user(request,
                                "Pay records have been approved successfully.",
                                level=messages.SUCCESS)
    else:
        modeladmin.message_user(request,
                                "Entries can only be approved if their status "
                                "is 'Completed'.", level=messages.ERROR)


def reject_payrun_action(modeladmin, request, queryset):
    """
    Reject the selected payrun entry.
    """
    # Retrieves the first PayRun from the queryset or None if empty.
    selected_payrun = queryset.first()

    # Retrieves the most recent PayRun or None if none exist.
    latest_payrun = get_latest_payrun()

    if check_single_payrun_selection(queryset, modeladmin, request) == False:
        return

    if check_latest_payrun(modeladmin, request, selected_payrun,
                           latest_payrun) == False:
        return

    if latest_payrun.status == PayRunStatusChoices.APPROVED:
        # APPROVED is a terminal state — downstream actions (payslips, payments)
        # may already have been triggered. Rejection from APPROVED is blocked here;
        # a dedicated super-user action with an audit trail is required instead.
        modeladmin.message_user(
            request,
            "An APPROVED pay run cannot be rejected. It is a terminal state. "
            "Contact a system administrator if a reversal is required.",
            level=messages.ERROR,
        )
        return

    if latest_payrun.status in [PayRunStatusChoices.COMPLETED,
                                PayRunStatusChoices.IN_PROGRESS,
                                PayRunStatusChoices.DUE]:

        latest_payrun.status = PayRunStatusChoices.REJECTED
        latest_payrun.save()

        modeladmin.message_user(request, "The payrun entry has been rejected.",
                                level=messages.SUCCESS)
    else:
        modeladmin.message_user(request,
                                "Entries can only be rejected if their status "
                                "is 'Completed' or 'Due'.",
                                level=messages.ERROR)


def run_payrun_action(modeladmin, request, queryset):
    """
    Queue a Celery task to process the selected payrun entry.
    """
    # Retrieves the first PayRun from the queryset or None if empty.
    selected_payrun = queryset.first()

    # Retrieves the most recent PayRun or None if none exist.
    latest_payrun = get_latest_payrun()

    if check_single_payrun_selection(queryset, modeladmin, request) == False:
        return

    if check_latest_payrun(modeladmin, request, selected_payrun,
                           latest_payrun) == False:
        return

    if latest_payrun.status == PayRunStatusChoices.APPROVED:
        modeladmin.message_user(request,
                                "The selected pay run has already been "
                                "approved.", level=messages.ERROR)

    elif latest_payrun.status == PayRunStatusChoices.COMPLETED:
        modeladmin.message_user(request,
                                "The pay run has been completed. To proceed, "
                                "please choose either 'Approve' or 'Reject'.",
                                level=messages.ERROR)

    elif latest_payrun.status == PayRunStatusChoices.IN_PROGRESS:
        modeladmin.message_user(request,
                                "We’re currently syncing your pay record. "
                                "Please hold on while we update your "
                                "information.", level=messages.SUCCESS)

    elif latest_payrun.status == PayRunStatusChoices.REJECTED:
        modeladmin.message_user(request,
                                "The pay records have been rejected."
                                "Please initiate a new pay run to proceed.",
                                level=messages.ERROR)

    elif latest_payrun.status == PayRunStatusChoices.DUE:

        payees = Payee.objects.filter(
            status='active',
            bankdetails__payee_acknowledgement=True)

        if payees.exists() == False:
            modeladmin.message_user(request,
                                    "No active payees found with acknowledged "
                                    "bank details. Please check and try again",
                                    level=messages.ERROR)

            latest_payrun.status = PayRunStatusChoices.REJECTED
            latest_payrun.save()
        else:
            run_pay_run_task.delay(latest_payrun.id)

            modeladmin.message_user(request,
                                    "Your pay run has been successfully "
                                    "started and is currently being processed.",
                                    level=messages.SUCCESS)


def is_payrun_exists(request):
    """
    Checks the status of the latest PayRun instance. If the status is DUE,
    COMPLETED, or IN_PROGRESS, it displays an error message and returns True,
    indicating that a new PayRun cannot be created until the existing one is
    finished. Otherwise, it returns False.
    """
    latest_payrun = get_latest_payrun()
    if latest_payrun:
        conflicting_statuses = [
            PayRunStatusChoices.DUE,
            PayRunStatusChoices.COMPLETED,
            PayRunStatusChoices.IN_PROGRESS
        ]
        if latest_payrun.status in conflicting_statuses:
            messages.error(request, (
                f"A Pay Run for {latest_payrun.get_month_name()} {latest_payrun.year} "
                f"already exists with the status '{latest_payrun.get_status_display()}'. "
                "Please finish that Pay Run before creating a new one."
            ))
            return True
    return False
