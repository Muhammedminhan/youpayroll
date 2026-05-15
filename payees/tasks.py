import logging
from celery import shared_task
from .models import Payee
from zohopeople.utils import get_payees_details

logger = logging.getLogger(__name__)

@shared_task
def fetch_details(payee_id):
    """
    Fetch payee details from Zoho and update local record.
    """
    payee = Payee.objects.filter(hrm_id=payee_id).first()
    if not payee:
        logger.error(f"Payee with HRM ID {payee_id} not found locally.")
        return

    try:
        response = get_payees_details(payee_id)
        if response and response.status_code == 200:
            response_data = response.json()
            res_obj = response_data.get("response", {})
            result_list = res_obj.get("result", [])
            if result_list:
                response_data_list = result_list[0]
            else:
                logger.warning(f"No result found in Zoho for payee {payee_id}")
                return
        else:
            status = response.status_code if response else 'None'
            logger.warning(f"Zoho API returned status {status} for {payee_id}")
            return
    except Exception:
        logger.exception(f"Unexpected error in fetch_details for {payee_id}")
        return
    
    if response_data_list:
        fetched_data = response_data_list.get('Employee', [])
        if isinstance(fetched_data, list) and fetched_data:
            fetched_data = fetched_data[0]
        else:
            fetched_data = None
            for key, value in response_data_list.items():
                if isinstance(value, list) and value:
                    fetched_data = value[0]
                    break
        
        if fetched_data:
            full_name = f"{fetched_data.get('FirstName', '')} {fetched_data.get('LastName', '')}".strip()
            if full_name:
                payee.full_name = full_name
            
            email = fetched_data.get("EmailID")
            if email:
                payee.email = email
                
            pan = fetched_data.get("Pan_Number")
            if pan:
                payee.pan_no = pan
                
            addr = fetched_data.get("Permanent_Address")
            if addr:
                payee.address = addr
                
            doj = fetched_data.get("Dateofjoining")
            if doj:
                payee.date_of_joining = doj
                
            payee.save()
