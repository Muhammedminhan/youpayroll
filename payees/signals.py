import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BankDetailsAck, BankDetails

logger = logging.getLogger(__name__)

@receiver(post_save, sender=BankDetailsAck)
def update_payee_acknowledgement(sender, instance, created, **kwargs):
    if created and instance.is_approved:
        payee = instance.payee
        # Use filter().order_by('-id').last() or first() to be deterministic
        bank_details = BankDetails.objects.filter(payee=payee).order_by('-id').first()
        if bank_details:
            bank_details.payee_acknowledgement = True
            bank_details.save(update_fields=['payee_acknowledgement'])
        else:
            logger.warning(f"Acknowledgement update skipped: No bank details found for payee {payee}")
