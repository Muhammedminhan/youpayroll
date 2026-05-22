from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import logging
import uuid

logger = logging.getLogger(__name__)
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from .models import (Profile, Payslip, Document, AdminNotification,
                     WikiCategory, WikiPage, UserNotification,
                     ensure_profile_completion_notification)
from .serializers import (
    ProfileSerializer, PayslipSerializer,
    BankDetailsSerializer,
    DocumentSerializer, AdminNotificationSerializer,
    WikiCategorySerializer, WikiPageSerializer,
    UserNotificationSerializer, UserSerializer
)

class UserNotificationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserNotificationSerializer

    def get_queryset(self):
        return UserNotification.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        ensure_profile_completion_notification(profile)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            ensure_profile_completion_notification(profile)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BankDetailsView(APIView):
    """Single source-of-truth for bank details.
    GET  → returns the payee's current BankDetails record.
    PATCH → updates it (resets payee_acknowledgement via the model's save()).
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_bank_details(self, request):
        from payees.models import BankDetails, Payee
        try:
            payee = Payee.objects.get(user=request.user)
        except Payee.DoesNotExist:
            return None, None
        bank_detail, _ = BankDetails.objects.get_or_create(payee=payee)
        return payee, bank_detail

    def get(self, request):
        _, bank_detail = self._get_bank_details(request)
        if bank_detail is None:
            return Response({'detail': 'No payee profile found for this user.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = BankDetailsSerializer(bank_detail)
        return Response(serializer.data)

    def patch(self, request):
        _, bank_detail = self._get_bank_details(request)
        if bank_detail is None:
            return Response({'detail': 'No payee profile found for this user.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = BankDetailsSerializer(bank_detail, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PayslipViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PayslipSerializer

    def get_queryset(self):
        queryset = Payslip.objects.filter(user=self.request.user)
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month:
            queryset = queryset.filter(month=month)
        if year:
            queryset = queryset.filter(year=year)
        return queryset

class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.debug(f"GoogleLoginView.post data: {request.data}")
        credential = request.data.get('credential')
        if not credential:
            logger.debug("Credential missing in request data")
            return Response({'error': 'Credential missing'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Securely verify the Google ID Token
            # This checks the signature, expiration, and audience (Client ID)
            idinfo = id_token.verify_oauth2_token(
                credential, 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            
            email = idinfo.get('email')
            
            if not email:
                return Response({'error': 'Email not found in token'}, status=status.HTTP_400_BAD_REQUEST)

            from payees.constants import YGG_EMAIL_DOMAIN
            email = email.lower()
            if not email.endswith(f"@{YGG_EMAIL_DOMAIN}"):
                return Response(
                    {'error': f'Please use a valid @{YGG_EMAIL_DOMAIN} email address.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # auto-creation behavior
                username = email.split('@')[0]
                # Ensure unique username
                if User.objects.filter(username=username).exists():
                    username = f"{username}_{uuid.uuid4().hex[:4]}"
                user = User(
                    email=email,
                    username=username,
                    first_name=idinfo.get('given_name', ''),
                    last_name=idinfo.get('family_name', '')
                )
                user.set_unusable_password()
                user.save()

            token, _ = Token.objects.get_or_create(user=user)
            
            # Fetch profile to return full data
            profile, _ = Profile.objects.get_or_create(user=user)
            serializer = ProfileSerializer(profile)
            data = serializer.data
            data['token'] = token.key
            return Response(data)

        except ValueError:
            # Invalid token
            return Response({'error': 'Invalid authentication token.'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Google login failed: {str(e)}")
            return Response({'error': 'An unexpected error occurred during login.'}, status=status.HTTP_400_BAD_REQUEST)

class AdminNotificationView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminNotificationSerializer
    queryset = AdminNotification.objects.filter(is_active=True)

class WikiCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = WikiCategorySerializer
    queryset = WikiCategory.objects.all()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        name = serializer.validated_data.get('name')
        # Wiki categories are usually created by admins, but we don't have an author field on the model.
        # Just ensuring slug is handled.
        serializer.save(slug=slugify(name))

class WikiPageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = WikiPageSerializer
    queryset = WikiPage.objects.all()
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        title = serializer.validated_data.get('title')
        slug = slugify(title)
        if WikiPage.objects.filter(slug=slug).exists():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        
        # Only set author if user is authenticated
        author = self.request.user if self.request.user.is_authenticated else None
        serializer.save(author=author, slug=slug)
