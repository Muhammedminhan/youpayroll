from encrypted_model_fields.fields import EncryptedCharField
from django.db import models


# Create your models here.

class ZohoPeopleFormToken(models.Model):
    access_token = EncryptedCharField(max_length=1024, null=False, blank=False)
    refresh_token = EncryptedCharField(max_length=1024, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']
