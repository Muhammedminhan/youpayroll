from unittest.mock import patch, MagicMock
from zohopeople.utils import generate_access_token, get_payees_details
from zohopeople.models import ZohoPeopleFormToken
from django.test import TestCase

class ZohoUtilsTest(TestCase):
    def setUp(self):
        ZohoPeopleFormToken.objects.create(
            access_token="old_access",
            refresh_token="valid_refresh"
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
        # Create an older row with a refresh token and a newer row WITHOUT a refresh token
        # The code should pick the row with the refresh token regardless of 'created' timestamp
        # if filter(refresh_token__isnull=False) is used.
        ZohoPeopleFormToken.objects.all().delete()
        
        target = ZohoPeopleFormToken.objects.create(
            access_token="target_access",
            refresh_token="target_refresh"
        )
        # Newer row but no refresh token
        ZohoPeopleFormToken.objects.create(
            access_token="newest_access",
            refresh_token=None
        )

        with patch('zohopeople.utils.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"access_token": "updated_access"}
            
            generate_access_token()
            
            target.refresh_from_db()
            self.assertEqual(target.access_token, "updated_access")

    @patch('zohopeople.utils.requests.post')
    def test_generate_access_token_failure(self, mock_post):
        mock_post.return_value.status_code = 400
        response = generate_access_token()
        self.assertIsNone(response)

    @patch('zohopeople.utils.requests.post')
    def test_get_payees_details_no_token(self, mock_post):
        ZohoPeopleFormToken.objects.all().delete()
        response = get_payees_details("HRM123")
        self.assertIsNone(response)
        self.assertEqual(mock_post.call_count, 0)

    @patch('zohopeople.utils.requests.post')
    def test_get_payees_details_retry_on_401(self, mock_post):
        # Sequence: 
        # 1. First call returns 401
        # 2. generate_access_token calls requests.post (returns 200)
        # 3. Recursive call returns 200
        
        mock_401 = MagicMock()
        mock_401.status_code = 401
        
        mock_200_token = MagicMock()
        mock_200_token.status_code = 200
        mock_200_token.json.return_value = {"access_token": "refreshed_access"}
        
        mock_200_data = MagicMock()
        mock_200_data.status_code = 200
        mock_200_data.json.return_value = {"response": {"result": [{"FirstName": "John"}]}}
        
        mock_post.side_effect = [mock_401, mock_200_token, mock_200_data]

        response = get_payees_details("HRM123")
        
        self.assertEqual(response.status_code, 200)
        # Verify 3 calls: 1st data attempt (401), token refresh, 2nd data attempt
        self.assertEqual(mock_post.call_count, 3)
