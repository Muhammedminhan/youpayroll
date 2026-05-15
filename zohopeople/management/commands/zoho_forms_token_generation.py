import json
import logging
from django.utils import timezone
from decouple import config
from django.core.management.base import BaseCommand
from zohopeople.constants import (GRANT_TYPE, ZP_API_REDIR_URI,
                                  ZP_API_ATOKEN_DOM_URL)
from zohopeople.models import ZohoPeopleFormToken
from zohopeople.utils import call_token_generation_api

logger = logging.getLogger(__name__)

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
        tgeneration_resp_val = tgeneration_resp.json()

        if 'access_token' in tgeneration_resp_val and 'refresh_token' in tgeneration_resp_val:
            # Store tokens in the DB.
            tokens = ZohoPeopleFormToken(
                access_token=tgeneration_resp_val['access_token'],
                refresh_token=tgeneration_resp_val['refresh_token'],
                last_refreshed_at=timezone.now()
            )
            tokens.save()
            stdout.write(style.SUCCESS("Tokens generated and stored successfully."))
        else:
            # Strict deny-list for redaction
            REDACTED_KEYS = ['access_token', 'refresh_token', 'id_token', 'client_secret']
            redacted_body = {k: v for k, v in tgeneration_resp_val.items() if k.lower() not in REDACTED_KEYS}
            stderr.write(style.ERROR(f"Error: Response missing tokens. Payload: {json.dumps(redacted_body)}"))
    else:
        status = tgeneration_resp.status_code if tgeneration_resp else "Network Error"
        body_summary = ""
        if tgeneration_resp:
            try:
                # Sanitize text response by redacting known sensitive keys before logging
                text = tgeneration_resp.text
                for key in ['access_token', 'refresh_token', 'client_secret']:
                    if key in text:
                        text = text.replace(key, "[REDACTED]")
                body_summary = f" Body: {text[:200]}"
            except Exception as e:
                logger.error(f"Error reading response text: {e}")
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
