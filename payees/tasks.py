import logging
from celery import shared_task
from django.db import IntegrityError
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
            logger.warning(f"No valid Employee record found in Zoho response for {payee_id}")
            return
        
        if fetched_data:
            updated_fields = []
            full_name = f"{fetched_data.get('FirstName', '')} {fetched_data.get('LastName', '')}".strip()
            if full_name and payee.full_name != full_name:
                payee.full_name = full_name
                updated_fields.append('full_name')
            
            email = fetched_data.get("EmailID")
            if email and payee.email != email:
                payee.email = email
                updated_fields.append('email')
                
            pan = fetched_data.get("Pan_Number")
            if pan and payee.pan_no != pan:
                payee.pan_no = pan
                updated_fields.append('pan_no')
                
            addr = fetched_data.get("Permanent_Address")
            if addr and payee.address != addr:
                payee.address = addr
                updated_fields.append('address')
                
            doj = fetched_data.get("Dateofjoining")
            if doj:
                from datetime import datetime
                parsed_date = None
                for fmt in ('%Y-%m-%d', '%d-%b-%Y', '%d-%B-%Y', '%Y/%m/%d', '%d/%m/%Y'):
                    try:
                        parsed_date = datetime.strptime(doj, fmt).date()
                        break
                    except ValueError:
                        continue
                new_doj = parsed_date.isoformat() if parsed_date else doj
                if payee.date_of_joining != new_doj:
                    payee.date_of_joining = new_doj
                    updated_fields.append('date_of_joining')
                
            if updated_fields:
                try:
                    payee.save(update_fields=updated_fields)
                except IntegrityError as e:
                    logger.error(f"IntegrityError saving payee {payee_id} with update_fields {updated_fields}: {e}")
