from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from rest_framework.authtoken.models import Token
from graphql import GraphQLError
from core.decorators import login_required
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

    def test_token_auth_succeeds(self):
        # A request with a valid DRF Token header should be authenticated correctly
        req = self.factory.post("/graphql/", HTTP_AUTHORIZATION=f"Token {self.token.key}")
        req.user = AnonymousUser()
        
        view = DRFTokenAuthGraphQLView()
        with patch("graphene_file_upload.django.FileUploadGraphQLView.dispatch", lambda s, r, *a, **k: r):
            result_req = view.dispatch(req)
            self.assertEqual(result_req.user, self.user)
            self.assertEqual(result_req.auth, self.token)
