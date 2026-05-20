import json
from django.utils import timezone
from decouple import config
from django.core.management.base import BaseCommand
from zohopeople.constants import (GRANT_TYPE, ZP_API_REDIR_URI,
                                  ZP_API_ATOKEN_DOM_URL)
from zohopeople.models import ZohoPeopleFormToken
from zohopeople.utils import call_token_generation_api


REDACTED_KEYS = {'access_token', 'refresh_token', 'id_token', 'client_secret', 'code'}

def redact_sensitive_data(data):
    """
    Recursively redacts sensitive keys from a dictionary or list, case-insensitively.
    """
    if isinstance(data, dict):
        return {
            k: ("[REDACTED]" if k.lower() in REDACTED_KEYS else redact_sensitive_data(v))
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data

def zoho_form_token_generation(grant_token, stdout, stderr, style):
    """
    Generate Access token for sending data to Zoho People
    and Refresh token to generate new Access token. Store both
    tokens in DB.
    """
    redirect_uri = config('ZOHOPEOPLE_REDIRECT_URI', default=ZP_API_REDIR_URI)

    tgeneration_data = {
        'grant_type': GRANT_TYPE,
        'client_id': config('ZOHOPEOPLE_CLIENT_ID'),
        'client_secret': config('ZOHOPEOPLE_CLIENT_SECRET'),
        'redirect_uri': redirect_uri,
        'code': grant_token
    }

    url = ZP_API_ATOKEN_DOM_URL
    tgeneration_resp = call_token_generation_api(url, tgeneration_data)

    if tgeneration_resp and tgeneration_resp.status_code == 200:
        try:
            tgeneration_resp_val = tgeneration_resp.json()
        except ValueError:
            stderr.write(style.ERROR(
                f"Error: Token endpoint returned HTTP 200 but body is not valid JSON "
                f"(body length: {len(tgeneration_resp.text)} chars)."
            ))
            return

        if 'access_token' in tgeneration_resp_val and 'refresh_token' in tgeneration_resp_val:
            # Store or update tokens in the DB using a concurrency-safe singleton pattern.
            from django.db import transaction, IntegrityError
            try:
                with transaction.atomic():
                    ZohoPeopleFormToken.objects.update_or_create(
                        id=1,
                        defaults={
                            'access_token': tgeneration_resp_val['access_token'],
                            'refresh_token': tgeneration_resp_val['refresh_token'],
                            'last_refreshed_at': timezone.now()
                        }
                    )
            except IntegrityError:
                # Fallback if updated concurrently by another process
                with transaction.atomic():
                    token_obj = ZohoPeopleFormToken.objects.select_for_update().get(id=1)
                    token_obj.access_token = tgeneration_resp_val['access_token']
                    token_obj.refresh_token = tgeneration_resp_val['refresh_token']
                    token_obj.last_refreshed_at = timezone.now()
                    token_obj.save()
            stdout.write(style.SUCCESS("Tokens generated and stored/updated successfully."))
        else:
            redacted_body = redact_sensitive_data(tgeneration_resp_val)
            stderr.write(style.ERROR(f"Error: Response missing tokens. Payload: {json.dumps(redacted_body)}"))
    else:
        status = tgeneration_resp.status_code if tgeneration_resp else "Network Error"
        body_summary = ""
        if tgeneration_resp:
            try:
                # Try to parse as JSON first and redact properly
                tgeneration_resp_val = tgeneration_resp.json()
                redacted_body = redact_sensitive_data(tgeneration_resp_val)
                body_summary = f" Payload: {json.dumps(redacted_body)}"
            except Exception:
                # If not JSON, only log status + length to avoid leaking raw body secrets
                body_summary = f" Body Length: {len(tgeneration_resp.text)} chars"
        stderr.write(style.ERROR(f"Error: Token generation failed. Status: {status}{body_summary}"))

class Command(BaseCommand):
    help = "Creates refresh tokens"

    def add_arguments(self, parser):
        parser.add_argument("--grant-token", type=str, help="OAuth grant token")

    def handle(self, *args, **options):
        grant_token = options.get("grant_token")
        if not grant_token:
            self.stderr.write(self.style.ERROR("Error: Grant token is required. Use --grant-token <token>"))
            return
            
        zoho_form_token_generation(grant_token, self.stdout, self.stderr, self.style)
