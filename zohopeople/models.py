from encrypted_model_fields.fields import EncryptedCharField
from django.db import models


# Create your models here.

class ZohoPeopleFormToken(models.Model):
    access_token = EncryptedCharField(max_length=1024, null=True, blank=True)
    refresh_token = EncryptedCharField(max_length=1024, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    # Singleton lock: always True, with a unique constraint to guarantee only one row.
    singleton_lock = models.BooleanField(default=True, editable=False)

    class Meta:
        ordering = ['-created']
        constraints = [
            models.UniqueConstraint(
                fields=['singleton_lock'],
                name='zoho_people_form_token_singleton'
            )
        ]

    def save(self, *args, **kwargs):
        # Force pk=1 and singleton_lock=True so update_or_create(id=1) always works
        # and the DB-level unique constraint prevents any second row.
        self.pk = 1
        self.singleton_lock = True
        super().save(*args, **kwargs)
