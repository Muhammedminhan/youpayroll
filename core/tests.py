from unittest.mock import ANY, patch
import datetime
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import User, AnonymousUser
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory
from graphql import GraphQLError
from core.decorators import login_required
from core.models import (UserNotification, ensure_profile_completion_notification)
from core.serializers import ProfileSerializer
from core.views import GoogleLoginView
from youpayroll.views import DRFTokenAuthGraphQLView


class DecoratorTest(TestCase):
    def test_login_required_unauthenticated(self):
        @login_required
        def dummy_resolver(root, info):
            return "success"
        
        class DummyContext:
            user = AnonymousUser()
        class DummyInfo:
            context = DummyContext()
            
        with self.assertRaises(GraphQLError) as ctx:
            dummy_resolver(None, DummyInfo())
        self.assertEqual(str(ctx.exception), "Authentication required.")

    def test_login_required_authenticated(self):
        @login_required
        def dummy_resolver(root, info):
            return "success"
            
        class DummyContext:
            pass
        user = User.objects.create_user(username="testuser", password="password")
        DummyContext.user = user
        class DummyInfo:
            context = DummyContext()
            
        result = dummy_resolver(None, DummyInfo())
        self.assertEqual(result, "success")

    def test_login_required_preserves_metadata(self):
        @login_required
        def my_resolver(root, info):
            """My resolver docstring"""
            return "success"
            
        self.assertEqual(my_resolver.__name__, "my_resolver")
        self.assertEqual(my_resolver.__doc__, "My resolver docstring")


class ProxySecuritySettingsTest(TestCase):
    def test_forwarded_for_middleware_runs_before_security_middleware(self):
        self.assertLess(
            settings.MIDDLEWARE.index('youpayroll.middleware.XForwardedForMiddleware'),
            settings.MIDDLEWARE.index('django.middleware.security.SecurityMiddleware'),
        )

    def test_forwarded_proto_https_marks_request_secure(self):
        request = RequestFactory().get(
            "/api/google-login/",
            HTTP_X_FORWARDED_PROTO="https",
        )

        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER, ('HTTP_X_FORWARDED_PROTO', 'https'))
        self.assertTrue(request.is_secure())


class ProfileCompletionNotificationTest(TestCase):
    def test_profile_save_does_not_create_action_required_notification(self):
        user = User.objects.create_user(username="profile_sync")
        profile = user.profile

        profile.designation = "Consultant"
        profile.save()

        self.assertFalse(
            UserNotification.objects.filter(
                user=user,
                notification_type="ACTION_REQUIRED",
            ).exists()
        )

    def test_explicit_profile_completion_check_creates_notification(self):
        user = User.objects.create_user(username="profile_incomplete")
        profile = user.profile

        ensure_profile_completion_notification(profile)

        notification = UserNotification.objects.get(
            user=user,
            notification_type="ACTION_REQUIRED",
        )
        self.assertEqual(notification.title, "Complete your profile")
        self.assertIn("First name", notification.message)

    def test_complete_profile_does_not_create_notification(self):
        user = User.objects.create_user(
            username="profile_complete",
            first_name="Complete",
            last_name="User",
        )
        profile = user.profile
        profile.designation = "Consultant"
        profile.gender = "Male"
        profile.dob = datetime.date(1990, 1, 1)
        profile.save()

        ensure_profile_completion_notification(profile)

        self.assertFalse(
            UserNotification.objects.filter(
                user=user,
                notification_type="ACTION_REQUIRED",
            ).exists()
        )


class GoogleLoginViewTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch("core.views.id_token.verify_oauth2_token")
    def test_rejects_non_ygg_google_accounts(self, mock_verify):
        mock_verify.return_value = {
            "email": "external@example.com",
            "given_name": "External",
            "family_name": "User",
        }

        request = self.factory.post("/api/google-login/", {"credential": "token"}, format="json")
        response = GoogleLoginView.as_view()(request)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email="external@example.com").exists())

    @patch("core.views.id_token.verify_oauth2_token")
    def test_created_google_users_have_unusable_passwords(self, mock_verify):
        mock_verify.return_value = {
            "email": "Consultant@yougotagift.com",
            "given_name": "Consultant",
            "family_name": "User",
        }

        request = self.factory.post("/api/google-login/", {"credential": "token"}, format="json")
        response = GoogleLoginView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        mock_verify.assert_called_once_with(
            "token",
            ANY,
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=settings.GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS,
        )
        user = User.objects.get(email="consultant@yougotagift.com")
        self.assertFalse(user.has_usable_password())

    @patch("core.views.id_token.verify_oauth2_token")
    def test_existing_user_lookup_is_case_insensitive(self, mock_verify):
        existing_user = User.objects.create_user(
            username="mixed_case_user",
            email="Consultant@YouGotaGift.com",
        )
        mock_verify.return_value = {
            "email": "consultant@yougotagift.com",
            "given_name": "Consultant",
            "family_name": "User",
        }

        request = self.factory.post("/api/google-login/", {"credential": "token"}, format="json")
        response = GoogleLoginView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        existing_user.refresh_from_db()
        self.assertEqual(existing_user.email, "consultant@yougotagift.com")

    @override_settings(
        TRUSTED_PROXY_IPS=['10.0.0.0/8'],
    )
    def test_google_login_throttle_uses_forwarded_client_ip_from_trusted_proxy(self):
        trusted_proxy_request = {
            'HTTP_X_FORWARDED_FOR': '203.0.113.9, 10.0.1.20',
            'REMOTE_ADDR': '10.0.2.30',
        }

        for _ in range(20):
            response = self.client.post('/api/google-login/', {}, format='json', **trusted_proxy_request)
            self.assertEqual(response.status_code, 400)
        throttled_response = self.client.post('/api/google-login/', {}, format='json', **trusted_proxy_request)

        self.assertEqual(throttled_response.status_code, 429)

        different_client_response = self.client.post(
            '/api/google-login/',
            {},
            format='json',
            HTTP_X_FORWARDED_FOR='203.0.113.10, 10.0.1.20',
            REMOTE_ADDR='10.0.2.30',
        )
        self.assertEqual(different_client_response.status_code, 400)

    @override_settings(
        TRUSTED_PROXY_IPS=['10.0.0.0/8'],
    )
    def test_google_login_throttle_ignores_forwarded_ip_from_untrusted_peer(self):
        for offset in range(20):
            response = self.client.post(
                '/api/google-login/',
                {},
                format='json',
                HTTP_X_FORWARDED_FOR=f'203.0.113.{offset}',
                REMOTE_ADDR='198.51.100.100',
            )
            self.assertEqual(response.status_code, 400)

        throttled_response = self.client.post(
            '/api/google-login/',
            {},
            format='json',
            HTTP_X_FORWARDED_FOR='203.0.113.22',
            REMOTE_ADDR='198.51.100.100',
        )
        self.assertEqual(throttled_response.status_code, 429)


class ProfilePictureValidationTest(TestCase):
    def test_profile_picture_rejects_gif_data_uri(self):
        user = User.objects.create_user(username="gif_profile")
        serializer = ProfileSerializer(
            user.profile,
            data={'profile_picture': 'data:image/gif;base64,R0lGODlhAQABAIAAAAUEBA=='},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('profile_picture', serializer.errors)


class HealthCheckTest(TestCase):
    def test_liveness_check_has_no_database_dependency(self):
        with patch("youpayroll.views.connection.cursor", side_effect=Exception("db down")):
            response = self.client.get("/health/live/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_legacy_health_check_has_no_database_dependency(self):
        with patch("youpayroll.views.connection.cursor", side_effect=Exception("db down")):
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_readiness_check_returns_ok_when_database_is_available(self):
        response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_readiness_check_returns_503_when_database_is_unavailable(self):
        with patch("youpayroll.views.connection.cursor", side_effect=Exception("db down")):
            response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.content, b"Service Unavailable")


class DRFTokenAuthGraphQLViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="tokenuser", password="password")
        self.token = Token.objects.create(user=self.user)

    def test_session_auth_bypassed(self):
        # Even if a request has a session-authenticated user, it should be ignored/rejected because it lacks a token
        req = self.factory.post("/graphql/")
        req.user = self.user  # Simulate SessionMiddleware setting user
        
        view = DRFTokenAuthGraphQLView()
        response = view.dispatch(req)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authentication credentials were not provided", response.content.decode())

    def test_invalid_token_rejected(self):
        req = self.factory.post("/graphql/", HTTP_AUTHORIZATION="Token invalidkey")
        req.user = AnonymousUser()
        
        view = DRFTokenAuthGraphQLView()
        response = view.dispatch(req)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid authentication credentials", response.content.decode())

    def test_token_auth_succeeds(self):
        # A request with a valid DRF Token header should be authenticated correctly
        req = self.factory.post("/graphql/", HTTP_AUTHORIZATION=f"Token {self.token.key}")
        req.user = AnonymousUser()
        
        view = DRFTokenAuthGraphQLView()
        with patch("graphene_file_upload.django.FileUploadGraphQLView.dispatch", lambda s, r, *a, **k: r):
            result_req = view.dispatch(req)
            self.assertEqual(result_req.user, self.user)
            self.assertEqual(result_req.auth, self.token)

    def test_options_request_bypasses_auth(self):
        # CORS preflight OPTIONS requests are sent without headers; they should bypass token auth completely
        req = self.factory.options("/graphql/")
        req.user = AnonymousUser()
        
        view = DRFTokenAuthGraphQLView()
        with patch("graphene_file_upload.django.FileUploadGraphQLView.dispatch", lambda s, r, *a, **k: "options_dispatched"):
            response = view.dispatch(req)
            self.assertEqual(response, "options_dispatched")


class GraphQLMaskingTest(TestCase):
    def setUp(self):
        from payees.models import Payee
        from payroll.models import PayRun, PayRecordRegister
        
        self.user = User.objects.create_user(username="testpayee", password="password")
        self.payee = Payee.objects.create(
            hrm_id="HR001",
            user=self.user,
            full_name="Test Payee"
        )
        self.pay_run = PayRun.objects.create(month=5, year=2026)
        self.register = PayRecordRegister.objects.create(
            payee=self.payee,
            pay_run=self.pay_run,
            amount=1000.00,
            account_number="1234567890",
            ifsc_code="IFSC001",
            micr_code="MICR001",
            swift_code="SWIFT001",
            branch_address="123 Main St"
        )

    def test_pay_record_register_graphql_masking(self):
        from graphene.test import Client
        from youpayroll.schema import schema

        query = """
        query {
            allPayRecordRegister {
                amount
                accountNumber
                ifscCode
                micrCode
                swiftCode
                branchAddress
            }
        }
        """
        class DummyContext:
            user = self.user

        client = Client(schema)
        result = client.execute(query, context=DummyContext())
        
        # Verify no errors occurred
        self.assertNotIn("errors", result)
        
        # Verify the returned data
        data = result["data"]["allPayRecordRegister"][0]
        self.assertEqual(float(data["amount"]), 1000.00)
        self.assertEqual(data["accountNumber"], "****7890")
        self.assertEqual(data["ifscCode"], "****")
        self.assertEqual(data["micrCode"], "****")
        self.assertEqual(data["swiftCode"], "****")
        self.assertEqual(data["branchAddress"], "****")

    def test_pay_record_register_graphql_masking_empty(self):
        from graphene.test import Client
        from youpayroll.schema import schema
        from payroll.models import PayRun, PayRecordRegister

        # Create another register with empty/None fields
        empty_register = PayRecordRegister.objects.create(
            payee=self.payee,
            pay_run=PayRun.objects.create(month=6, year=2026),
            amount=500.00,
            account_number=None,
            ifsc_code="",
            micr_code=None,
            swift_code="",
            branch_address=None
        )

        query = """
        query {
            allPayRecordRegister {
                amount
                accountNumber
                ifscCode
                micrCode
                swiftCode
                branchAddress
            }
        }
        """
        class DummyContext:
            user = self.user

        client = Client(schema)
        result = client.execute(query, context=DummyContext())
        
        self.assertNotIn("errors", result)
        
        # Since order_by is -record_created, the empty_register is the first one in response
        data = result["data"]["allPayRecordRegister"][0]
        self.assertEqual(float(data["amount"]), 500.00)
        self.assertEqual(data["accountNumber"], "")
        self.assertEqual(data["ifscCode"], "")
        self.assertEqual(data["micrCode"], "")
        self.assertEqual(data["swiftCode"], "")
        self.assertEqual(data["branchAddress"], "")


class PayrollRESTMaskingTest(TestCase):
    def setUp(self):
        from payees.models import Payee
        from payroll.models import PayRun, PayRecordRegister

        self.client = APIClient()
        self.user = User.objects.create_user(username="restpayee", password="password")
        self.payee = Payee.objects.create(
            hrm_id="HRREST001",
            user=self.user,
            full_name="REST Payee",
        )
        self.client.force_authenticate(user=self.user)
        self.pay_run = PayRun.objects.create(month=5, year=2026)
        self.register = PayRecordRegister.objects.create(
            payee=self.payee,
            pay_run=self.pay_run,
            amount=1000.00,
            account_number="1234567890",
            ifsc_code="IFSC001",
            micr_code="MICR001",
            swift_code="SWIFT001",
            branch_address="123 Main St",
        )

    def test_pay_record_register_rest_masks_bank_details(self):
        response = self.client.get('/api/payroll/registers/')

        self.assertEqual(response.status_code, 200)
        data = response.json()[0]
        self.assertEqual(data["account_number"], "****7890")
        self.assertEqual(data["ifsc_code"], "****")
        self.assertEqual(data["micr_code"], "****")
        self.assertEqual(data["swift_code"], "****")
        self.assertEqual(data["branch_address"], "****")
