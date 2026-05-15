import logging
import json
import requests
from decouple import config
from requests.exceptions import HTTPError
from requests.exceptions import ConnectionError
from requests.exceptions import Timeout
from requests.exceptions import RequestException
from .models import ZohoPeopleFormToken
from .constants import ZP_EMPLOYEE_DETAILS_API, ZP_API_ATOKEN_DOM_URL

logger = logging.getLogger(__name__)


def call_token_generation_api(url, data):
    """ Generate tokens"""
    response = None
    try:
        response = requests.post(url=url, data=data, timeout=30)
        response.raise_for_status()
        logger.info("Token generation is successful")
    except HTTPError as errh:
        logger.warning(f"Http Error:{errh}")
    except ConnectionError as errc:
        logger.warning(f"Error Connecting:{errc}")
    except Timeout as errt:
        logger.warning(f"Timeout Error:{errt}")
    except RequestException as err:
        logger.warning(f"OOps: Something Else:{err}")

    return response


# function to generate access token from refresh token
# Generates access token from already generated refresh token from DB
def generate_access_token():
    """Calls the zoho people API to generate access token. The Refresh token is

    taken from the DB. if refresh token is not present in DB, It is needed to
    generate using custom commands
    """
    token_obj = ZohoPeopleFormToken.objects.filter(refresh_token__isnull=False).last()
    if not token_obj:
        logger.error("No refresh token found in database.")
        return None
    refresh_token = token_obj.refresh_token
    url = ZP_API_ATOKEN_DOM_URL
    data = {
        "refresh_token": refresh_token,
        "client_id": config("ZOHOPEOPLE_CLIENT_ID"),
        "client_secret": config("ZOHOPEOPLE_CLIENT_SECRET"),
        "grant_type": "refresh_token"
    }
    response = requests.post(url=url, data=data, timeout=30)
    if response.status_code == 200:
        # Update the existing token row instead of accumulating rows
        token_obj.access_token = response.json().get("access_token")
        token_obj.save(update_fields=['access_token'])
        return response
    else:
        logger.warning("OOps: Some Error Occurred")
        return response


# Function returns the latest Access token from DB.
def get_emp_access_token():
    """Fetch Access token from the DB and return the latest Access
    token.
    """
    latest_token_obj = ZohoPeopleFormToken.objects.latest('created')
    return latest_token_obj.access_token


# Function to call zoho people API to get the details of payees
def get_payees_details(emp_id, retry=True):
    """
    Calls the zoho people API to get the details of payees
    """
    access_token = get_emp_access_token()
    url = ZP_EMPLOYEE_DETAILS_API
    search_params = {"searchField": 'EmployeeID',
                     "searchOperator": 'Is',
                     "searchText": str(emp_id)}
    headers = {
        "Authorization": "Zoho-oauthtoken " + access_token,
        "Content-Type": "application/x-www-form-urlencoded",

    }

    body = {"searchParams": json.dumps(search_params)}

    response = requests.post(url=url, headers=headers, params=body, timeout=30)
    if response.status_code == 200:
        return response

    elif response.status_code == 401 and retry:
        generate_access_token()
        response = get_payees_details(emp_id, retry=False)
        if response.status_code == 200:
            return response

    else:
        logger.warning("OOps: Some Error Occurred")
    return response
