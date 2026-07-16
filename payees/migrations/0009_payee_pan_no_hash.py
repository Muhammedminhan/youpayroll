# Generated migration: adds pan_no_hash for deterministic uniqueness on encrypted PAN.
# Also backfills pan_no_hash for any existing rows that already have a PAN stored.
# NOTE: existing pan_no values stored as plaintext (before migration 0008) cannot be
# automatically re-encrypted here; run the management command encrypt_existing_pans
# (or a one-time data script) after deploying this migration to encrypt legacy rows.

import hashlib
import hmac
from django.conf import settings
from django.db import migrations, models


def backfill_pan_hashes(apps, schema_editor):
    Payee = apps.get_model('payees', 'Payee')
    key = (getattr(settings, 'PAN_HASH_KEY', None) or settings.SECRET_KEY).encode()
    to_update = []
    for payee in Payee.objects.filter(pan_no__isnull=False).exclude(pan_no=''):
        pan_hash = hmac.new(key, payee.pan_no.upper().encode(), hashlib.sha256).hexdigest()
        payee.pan_no_hash = pan_hash
        to_update.append(payee)
    if to_update:
        Payee.objects.bulk_update(to_update, ['pan_no_hash'])


def reverse_backfill(apps, schema_editor):
    Payee = apps.get_model('payees', 'Payee')
    Payee.objects.update(pan_no_hash=None)


class Migration(migrations.Migration):

    dependencies = [
        ('payees', '0008_alter_bankdetails_account_no_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payee',
            name='pan_no_hash',
            field=models.CharField(blank=True, editable=False, max_length=64, null=True),
        ),
        migrations.RunPython(backfill_pan_hashes, reverse_code=reverse_backfill),
        migrations.AlterField(
            model_name='payee',
            name='pan_no_hash',
            field=models.CharField(blank=True, editable=False, max_length=64, null=True, unique=True),
        ),
    ]
