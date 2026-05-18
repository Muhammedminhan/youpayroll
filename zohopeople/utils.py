import logging
import json
import requests
from django.utils import timezone
from django.db import transaction
from decouple import config
from requests.exceptions import RequestException
from .models import ZohoPeopleFormToken
from .constants import ZP_EMPLOYEE_DETAILS_API, ZP_API_ATOKEN_DOM_URL, NEW_GRANT_TYPE

logger = logging.getLogger(__name__)


def call_token_generation_api(url, data):
    """ Generate tokens """
    try:
        response = requests.post(url=url, data=data, timeout=30)
        if response.status_code == 200:
            logger.info("Token generation is successful")
            return response
        else:
            logger.warning(f"Token generation failed. Status: {response.status_code}")
            return None
    except RequestException as err:
        logger.error(f"Network error in token generation API at {url}: {err}")
        return None


def generate_access_token(force=False):
    """
    Calls the zoho people API to generate access token using refresh token.
    Uses a lightweight check before entering a blocking network call.
    """
    url = ZP_API_ATOKEN_DOM_URL
    
    token_obj = ZohoPeopleFormToken.objects.filter(
        refresh_token__isnull=False
    ).order_by('-created').first()

    if not token_obj:
        logger.error("No refresh token found in database.")
        return None

    if not force and token_obj.access_token and token_obj.last_refreshed_at:
        if (timezone.now() - token_obj.last_refreshed_at).total_seconds() < 300:
            logger.info("Token was recently refreshed. Skipping network call.")
            resp = requests.Response()
            resp.status_code = 200
            resp._content = b'{"status": "cached"}'
            return resp

    refresh_token = token_obj.refresh_token
    data = {
        "refresh_token": refresh_token,
        "client_id": config("ZOHOPEOPLE_CLIENT_ID"),
        "client_secret": config("ZOHOPEOPLE_CLIENT_SECRET"),
        "grant_type": NEW_GRANT_TYPE
    }

    try:
        response = requests.post(url=url, data=data, timeout=30)
        if response.status_code == 200:
            resp_data = response.json()
            access_token = resp_data.get("access_token")
            
            if not access_token:
                logger.error(f"Zoho returned 200 but no access_token in body. Error: {resp_data.get('error')}")
                return None

            with transaction.atomic():
                locked_token = ZohoPeopleFormToken.objects.select_for_update().get(pk=token_obj.pk)
                locked_token.access_token = access_token
                locked_token.last_refreshed_at = timezone.now()
                locked_token.save(update_fields=['access_token', 'last_refreshed_at'])
            
            return response
        else:
            logger.warning(f"Failed to generate access token. Status: {response.status_code}")
            return None
    except RequestException as e:
        logger.error(f"Network error during access token generation: {e}")
        return None


def get_emp_access_token():
    """Fetch Access token from the DB and return the latest Access token."""
    latest_token_obj = ZohoPeopleFormToken.objects.filter(
        refresh_token__isnull=False, access_token__isnull=False
    ).order_by('-created').only('access_token').first()
    if not latest_token_obj:
        return None
    return latest_token_obj.access_token


def get_payees_details(emp_id, retry=True):
    """Calls the zoho people API to get the details of payees."""
    access_token = get_emp_access_token()
    if not access_token:
        return None

    url = ZP_EMPLOYEE_DETAILS_API
    search_params = {"searchField": 'EmployeeID', "searchOperator": 'Is', "searchText": str(emp_id)}
    headers = {
        "Authorization": "Zoho-oauthtoken " + access_token,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = {"searchParams": json.dumps(search_params)}

    try:
        response = requests.post(url=url, headers=headers, data=body, timeout=30)
        if response.status_code == 200:
            return response
        elif response.status_code == 401 and retry:
            gen_resp = generate_access_token(force=True)
            if gen_resp and gen_resp.status_code == 200:
                return get_payees_details(emp_id, retry=False)
            return None
        elif response.status_code == 401 and not retry:
            logger.error(f"Zoho API returned 401 even after token refresh for emp_id {emp_id}.")
            return None
        else:
            logger.warning(f"Zoho API error for emp_id {emp_id}. Status: {response.status_code}")
            return None
    except RequestException as e:
        logger.error(f"Network error calling Zoho API for emp_id {emp_id}: {e}")
        return None
