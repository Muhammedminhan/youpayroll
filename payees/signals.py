import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BankDetailsAck

logger = logging.getLogger(__name__)

@receiver(post_save, sender=BankDetailsAck)
def update_payee_acknowledgement(sender, instance, created, **kwargs):
    """
    Mark bank details as acknowledged when an approval is recorded.
    """
    if instance.is_approved:
        # Use the explicit relation instead of non-deterministic lookup
        bank_details = instance.bank_details
        if bank_details:
            bank_details.payee_acknowledgement = True
            bank_details.save(update_fields=['payee_acknowledgement'])
        else:
            logger.warning(f"Acknowledgement update skipped: No specific bank_details linked to Ack {instance.pk}")
