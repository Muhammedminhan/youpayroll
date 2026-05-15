import unittest
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

    @patch('requests.post')
    def test_generate_access_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new_access"}
        mock_post.return_value = mock_response

        response = generate_access_token()
        
        self.assertEqual(response.status_code, 200)
        token_obj = ZohoPeopleFormToken.objects.latest('created')
        self.assertEqual(token_obj.access_token, "new_access")

    @patch('requests.post')
    def test_get_payees_details_retry_on_401(self, mock_post):
        # First call returns 401, second (after refresh) returns 200
        mock_401 = MagicMock()
        mock_401.status_code = 401
        
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"response": {"result": [{"FirstName": "John"}]}}
        
        mock_post.side_effect = [mock_401, mock_200, mock_200] # refresh call, then second attempt

        # Mock generate_access_token to succeed
        with patch('zohopeople.utils.generate_access_token') as mock_gen:
            mock_gen.return_value = mock_200
            response = get_payees_details("HRM123")
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_gen.call_count, 1)
