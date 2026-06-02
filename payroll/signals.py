import logging
from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import post_save
from .models import Form16

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Form16)
def extract_zip_and_create_entries(sender, instance, created, **kwargs):
    """
    This method extracts the uploaded ZIP file and assigns each Form16 PDF
    to the corresponding payee by matching the PAN number.
    Dispatches to Celery to avoid blocking.
    """
    if not created or not instance.form16_zip_file or instance.is_extracted:
        return
        
    from payroll.tasks import extract_form16_zip_task

    def dispatch_extraction_task():
        extract_form16_zip_task.delay(instance.pk)
        logger.info(f"Dispatched Form16 extraction task for ID {instance.pk}")

    transaction.on_commit(dispatch_extraction_task)
