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
        else:
            logger.warning(f"Token generation failed. Status: {response.status_code}")
        return response
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
        id=1,
        refresh_token__isnull=False
    ).first()

    if not token_obj:
        logger.error("No refresh token found in database.")
        return None

    # Outer (unguarded) freshness check — performance optimisation only.
    # This read is intentionally not under a lock: two workers may both pass
    # this check and both enter the transaction below. That is safe because the
    # inner select_for_update() re-check is the authoritative guard that prevents
    # a double-refresh. The outer check just avoids acquiring the DB lock on the
    # common "token is still fresh" path.
    if not force and token_obj.access_token and token_obj.last_refreshed_at:
        if (timezone.now() - token_obj.last_refreshed_at).total_seconds() < 300:
            logger.info("Token was recently refreshed. Skipping network call.")
            return {"status": "cached", "access_token": token_obj.access_token}

    try:
        with transaction.atomic():
            locked_token = ZohoPeopleFormToken.objects.select_for_update().get(pk=token_obj.pk)

            # Authoritative re-check under the lock — prevents concurrent workers
            # from both passing the outer check and both calling the Zoho API.
            if not force and locked_token.access_token and locked_token.last_refreshed_at:
                if (timezone.now() - locked_token.last_refreshed_at).total_seconds() < 300:
                    logger.info("Token was refreshed by another worker. Skipping network call.")
                    return {"status": "cached", "access_token": locked_token.access_token}

            refresh_token = locked_token.refresh_token
            data = {
                "refresh_token": refresh_token,
                "client_id": config("ZOHOPEOPLE_CLIENT_ID"),
                "client_secret": config("ZOHOPEOPLE_CLIENT_SECRET"),
                "grant_type": NEW_GRANT_TYPE
            }

            response = requests.post(url=url, data=data, timeout=30)
            if response.status_code == 200:
                resp_data = response.json()
                access_token = resp_data.get("access_token")
                
                if not access_token:
                    logger.error(f"Zoho returned 200 but no access_token in body. Error: {resp_data.get('error')}")
                    return {"status": "failed", "error": "No access token in response"}

                rotated_refresh_token = resp_data.get("refresh_token")
                locked_token.access_token = access_token
                locked_token.last_refreshed_at = timezone.now()
                
                update_fields = ['access_token', 'last_refreshed_at']
                if rotated_refresh_token:
                    logger.info("Zoho returned a rotated refresh_token. Persisting it.")
                    locked_token.refresh_token = rotated_refresh_token
                    update_fields.append('refresh_token')
                
                locked_token.save(update_fields=update_fields)
                
                return {"status": "success", "access_token": access_token}
            else:
                logger.warning(f"Failed to generate access token. Status: {response.status_code}")
                return {"status": "failed", "error": f"HTTP {response.status_code}"}
    except RequestException as e:
        logger.error(f"Network error during access token generation: {e}")
        return {"status": "failed", "error": str(e)}


def get_emp_access_token():
    """Fetch Access token from the DB and return the latest Access token."""
    latest_token_obj = ZohoPeopleFormToken.objects.filter(
        id=1, refresh_token__isnull=False, access_token__isnull=False
    ).only('access_token').first()
    if not latest_token_obj:
        return None
    return latest_token_obj.access_token


def get_payees_details(emp_id, access_token=None):
    """Calls the zoho people API to get the details of payees using a bounded loop counter to manage retries."""
    url = ZP_EMPLOYEE_DETAILS_API
    search_params = {"searchField": 'EmployeeID', "searchOperator": 'Is', "searchText": str(emp_id)}
    body = {"searchParams": json.dumps(search_params)}

    for attempt in range(2):
        if not access_token:
            access_token = get_emp_access_token()
        if not access_token:
            if attempt == 0:
                # Force refresh token immediately if no token is found in database
                gen_resp = generate_access_token(force=True)
                if gen_resp and gen_resp.get("status") in ("success", "cached"):
                    access_token = gen_resp.get("access_token")
                    continue
            return None

        headers = {
            "Authorization": "Zoho-oauthtoken " + access_token,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = requests.post(url=url, headers=headers, data=body, timeout=30)
            if response.status_code == 200:
                return response
            elif response.status_code == 401 and attempt == 0:
                logger.info(f"Zoho API returned 401. Forcing token refresh and retrying.")
                gen_resp = generate_access_token(force=True)
                if gen_resp and gen_resp.get("status") in ("success", "cached"):
                    access_token = gen_resp.get("access_token")
                    # Clear access_token variable from parameter to read fresh from gen_resp
                    continue
                return None
            elif response.status_code == 401:
                logger.error(f"Zoho API returned 401 even after token refresh for emp_id {emp_id}.")
                return None
            else:
                logger.warning(f"Zoho API error for emp_id {emp_id}. Status: {response.status_code}")
                return None
        except RequestException as e:
            logger.error(f"Network error calling Zoho API for emp_id {emp_id}: {e}")
            return None

    return None
