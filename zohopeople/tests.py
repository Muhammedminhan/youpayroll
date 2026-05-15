from unittest.mock import patch, MagicMock
from django.utils import timezone
from zohopeople.utils import generate_access_token, get_payees_details
from zohopeople.models import ZohoPeopleFormToken
from django.test import TestCase

class ZohoUtilsTest(TestCase):
    def setUp(self):
        ZohoPeopleFormToken.objects.create(
            access_token="old_access",
            refresh_token="valid_refresh",
            last_refreshed_at=timezone.now() - timezone.timedelta(hours=1)
        )

    @patch('zohopeople.utils.requests.post')
    def test_generate_access_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new_access"}
        mock_post.return_value = mock_response

        response = generate_access_token()
        
        self.assertEqual(response.status_code, 200)
        token_obj = ZohoPeopleFormToken.objects.latest('created')
        self.assertEqual(token_obj.access_token, "new_access")

    def test_generate_access_token_multi_row_ordering(self):
        ZohoPeopleFormToken.objects.all().delete()
        
        old_row = ZohoPeopleFormToken.objects.create(
            access_token="old_access",
            refresh_token="old_refresh"
        )
        old_time = timezone.now() - timezone.timedelta(hours=1)
        ZohoPeopleFormToken.objects.filter(pk=old_row.pk).update(created=old_time)
        
        new_row = ZohoPeopleFormToken.objects.create(
            access_token="new_access",
            refresh_token="new_refresh"
        )

        with patch('zohopeople.utils.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"access_token": "updated_access"}
            
            generate_access_token()
            
            new_row.refresh_from_db()
            self.assertEqual(new_row.access_token, "updated_access")
            
            old_row.refresh_from_db()
            self.assertEqual(old_row.access_token, "old_access")

    @patch('zohopeople.utils.requests.post')
    def test_get_payees_details_refresh_failure(self, mock_post):
        # Ensure the mock side_effect matches the exact expected calls
        mock_401 = MagicMock()
        mock_401.status_code = 401
        mock_400 = MagicMock()
        mock_400.status_code = 400
        
        # 1st call (employee) -> 401
        # 2nd call (token refresh) -> 400
        mock_post.side_effect = [mock_401, mock_400]
        
        response = get_payees_details("HRM123")
        self.assertIsNone(response)
        self.assertEqual(mock_post.call_count, 2)
