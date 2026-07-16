from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserProfileView, PayslipViewSet,
    BankDetailsView,
    DocumentViewSet, AdminNotificationView,
    WikiCategoryViewSet, WikiPageViewSet, UserNotificationViewSet,
    GoogleLoginView, LogoutView,
)

router = DefaultRouter()
router.register(r'payslips', PayslipViewSet, basename='payslip')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'wiki-categories', WikiCategoryViewSet, basename='wiki-category')
router.register(r'wiki-pages', WikiPageViewSet, basename='wiki-page')
router.register(r'user-notifications', UserNotificationViewSet, basename='user-notification')

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('bank-details/', BankDetailsView.as_view(), name='bank_details'),
    path('google-login/', GoogleLoginView.as_view(), name='google_login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('notifications/', AdminNotificationView.as_view(), name='notifications'),
    path('', include(router.urls)),
]

