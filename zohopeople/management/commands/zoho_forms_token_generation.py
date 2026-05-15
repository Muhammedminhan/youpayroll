from decouple import config
from django.core.management.base import BaseCommand
from zohopeople.constants import (GRANT_TYPE, ZP_API_REDIR_URI,
                                  ZP_API_ATOKEN_DOM_URL)
from zohopeople.models import ZohoPeopleFormToken
from zohopeople.utils import call_token_generation_api


def zoho_form_token_generation(grant_token, stdout, stderr, style):
    """
    Generate Access token for sending data to Zoho People
    and Refresh token to generate new Access token. Store both
    tokens in DB.
    """
    tgeneration_data = {
        'grant_type': GRANT_TYPE,
        'client_id': config('ZOHOPEOPLE_CLIENT_ID'),
        'client_secret': config('ZOHOPEOPLE_CLIENT_SECRET'),
        'redirect_uri': ZP_API_REDIR_URI,
        'code': grant_token
    }

    url = ZP_API_ATOKEN_DOM_URL
    # Send Post request for generating tokens.
    tgeneration_resp = call_token_generation_api(url, tgeneration_data)

    if tgeneration_resp and tgeneration_resp.status_code == 200:
        tgeneration_resp_val = tgeneration_resp.json()

        if 'access_token' in tgeneration_resp_val and 'refresh_token' in tgeneration_resp_val:
            # Store tokens in the DB.
            tokens = ZohoPeopleFormToken(
                access_token=tgeneration_resp_val['access_token'],
                refresh_token=tgeneration_resp_val['refresh_token'])
            tokens.save()
            stdout.write(style.SUCCESS("Tokens generated and stored successfully."))
        else:
            stderr.write(style.ERROR(f"Error: Response missing tokens. Response: {tgeneration_resp_val}"))
    else:
        status = tgeneration_resp.status_code if tgeneration_resp else "No Response"
        body = tgeneration_resp.text if tgeneration_resp else ""
        stderr.write(style.ERROR(f"Error: Token generation failed. Status: {status}, Body: {body}"))


class Command(BaseCommand):
    help = "Creates refresh tokens"

    def add_arguments(self, parser):
        parser.add_argument("--grant-token", type=str, help="OAuth grant token")

    def handle(self, *args, **options):
        grant_token = options.get("grant_token")
        
        if not grant_token:
            self.stdout.write("Please provide the Zoho OAuth Grant Token.")
            grant_token = input("Grant Token: ").strip()
        
        if not grant_token:
            self.stdout.write(self.style.ERROR("Error: Grant token is required."))
            return
            
        zoho_form_token_generation(grant_token, self.stdout, self.stderr, self.style)
