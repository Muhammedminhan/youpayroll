from unittest.mock import patch, MagicMock
from django.utils import timezone
from zohopeople.utils import generate_access_token, get_payees_details
from zohopeople.models import ZohoPeopleFormToken
from django.test import TestCase

class ZohoUtilsTest(TestCase):
    def setUp(self):
        # Create a seed token to avoid empty-table failures
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

    @patch('zohopeople.utils.requests.post')
    def test_generate_access_token_empty_table(self, mock_post):
        # Test behavior when no seed token exists
        ZohoPeopleFormToken.objects.all().delete()
        response = generate_access_token()
        self.assertIsNone(response)
        self.assertEqual(mock_post.call_count, 0)

    @patch('zohopeople.utils.requests.post')
    def test_generate_access_token_recent_buffer_skip(self, mock_post):
        # Set last_refreshed_at to 1 minute ago
        token = ZohoPeopleFormToken.objects.latest('created')
        token.last_refreshed_at = timezone.now() - timezone.timedelta(minutes=1)
        token.save()
        
        response = generate_access_token()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "cached")
        self.assertEqual(mock_post.call_count, 0)

    @patch('zohopeople.utils.requests.post')
    def test_get_payees_details_refresh_failure(self, mock_post):
        # 1. First call (employee fetch) -> 401
        # 2. Second call (token refresh) -> 400
        mock_401 = MagicMock()
        mock_401.status_code = 401
        mock_400 = MagicMock()
        mock_400.status_code = 400
        
        mock_post.side_effect = [mock_401, mock_400]
        
        response = get_payees_details("HRM123")
        self.assertIsNone(response)
        self.assertEqual(mock_post.call_count, 2)
