from unittest.mock import patch, MagicMock
from django.contrib import admin
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase
from django.utils import timezone
from datetime import timedelta
from zohopeople.admin import ZohoPeopleFormTokenAdmin
from zohopeople.utils import generate_access_token, get_payees_details
from zohopeople.models import ZohoPeopleFormToken


class ZohoPeopleFormTokenAdminTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = ZohoPeopleFormTokenAdmin(ZohoPeopleFormToken, admin.site)

    def test_module_permission_is_superuser_only(self):
        superuser = User.objects.create_superuser(
            username='zoho_admin',
            email='zoho_admin@example.com',
            password='password',
        )
        staff_user = User.objects.create_user(username='zoho_staff', is_staff=True)

        request = self.factory.get('/admin/zohopeople/')
        request.user = superuser
        self.assertTrue(self.admin.has_module_permission(request))

        request.user = staff_user
        self.assertFalse(self.admin.has_module_permission(request))

        request.user = AnonymousUser()
        self.assertFalse(self.admin.has_module_permission(request))

    def test_token_singleton_cannot_be_deleted_from_admin(self):
        superuser = User.objects.create_superuser(
            username='zoho_delete_admin',
            email='zoho_delete_admin@example.com',
            password='password',
        )

        request = self.factory.get('/admin/zohopeople/zohopeopleformtoken/')
        request.user = superuser

        self.assertFalse(self.admin.has_delete_permission(request))


class ZohoUtilsTest(TestCase):
    def setUp(self):
        # Create a seed token to avoid empty-table failures
        ZohoPeopleFormToken.objects.create(
            access_token="old_access",
            refresh_token="valid_refresh",
            last_refreshed_at=timezone.now() - timedelta(hours=1)
        )
        self.config_patcher = patch('zohopeople.utils.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.side_effect = lambda key, *args, **kwargs: {
            'ZOHOPEOPLE_CLIENT_ID': 'dummy_client_id',
            'ZOHOPEOPLE_CLIENT_SECRET': 'dummy_client_secret',
        }.get(key, kwargs.get('default') if 'default' in kwargs else 'dummy_val')

    def tearDown(self):
        self.config_patcher.stop()

    @patch('zohopeople.utils.requests.post')
    def test_generate_access_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new_access"}
        mock_post.return_value = mock_response

        response = generate_access_token()
        
        self.assertEqual(response.get("status"), "success")
        self.assertEqual(response.get("access_token"), "new_access")
        token_obj = ZohoPeopleFormToken.objects.get(id=1)
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
        token = ZohoPeopleFormToken.objects.get(id=1)
        token.last_refreshed_at = timezone.now() - timedelta(minutes=1)
        token.save()
        
        response = generate_access_token()
        
        self.assertEqual(response.get("status"), "cached")
        self.assertEqual(response.get("access_token"), "old_access")
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

    @patch('zohopeople.utils.requests.post')
    def test_get_payees_details_refresh_success(self, mock_post):
        # 1. First call (employee fetch) -> 401 Unauthorized
        # 2. Second call (token refresh) -> 200 OK with fresh token
        # 3. Third call (retried employee fetch) -> 200 OK with payee details
        mock_401 = MagicMock()
        mock_401.status_code = 401
        
        mock_refresh = MagicMock()
        mock_refresh.status_code = 200
        mock_refresh.json.return_value = {"access_token": "brand_new_token"}
        
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"status": "success", "data": "employee_data"}
        
        mock_post.side_effect = [mock_401, mock_refresh, mock_success]
        
        response = get_payees_details("HRM123")
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_post.call_count, 3)
        
        # Verify that the third request used the brand new token in authorization header
        third_call_headers = mock_post.call_args_list[2][1]['headers']
        self.assertEqual(third_call_headers['Authorization'], "Zoho-oauthtoken brand_new_token")

    @patch('zohopeople.utils.requests.post')
    def test_generate_access_token_with_rotation(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "brand_new_access",
            "refresh_token": "brand_new_rotated_refresh"
        }
        mock_post.return_value = mock_response

        response = generate_access_token()
        
        self.assertEqual(response.get("status"), "success")
        self.assertEqual(response.get("access_token"), "brand_new_access")
        
        token_obj = ZohoPeopleFormToken.objects.get(id=1)
        self.assertEqual(token_obj.access_token, "brand_new_access")
        # Assert that the rotated refresh token was successfully persisted!
        self.assertEqual(token_obj.refresh_token, "brand_new_rotated_refresh")
