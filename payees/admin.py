import logging
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html
from payees.constants import RESTRICTED_PAYEE_GROUPS
from payroll.admin import Form16Inline
from .models import (Payee, BankDetails, BankDetailsAck)
from .utils import restrict_queryset_by_group
from .tasks import fetch_details

logger = logging.getLogger(__name__)


class CustomUserAdmin(BaseUserAdmin):

    def get_list_filter(self, request):
        # Restrict filters for users in restricted groups
        if request.user.groups.filter(name__in=RESTRICTED_PAYEE_GROUPS).exists():
            return ()  # Return empty tuple to hide all filters
        return super().get_list_filter(request)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return restrict_queryset_by_group(qs, request.user)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


class PayeeAdmin(admin.ModelAdmin):
    inlines = [Form16Inline]
    list_display = ["hrm_id", "full_name", "tds_type", "status", "user"]
    readonly_fields = ["full_name", "email", "pan_no", "address",
                       "date_of_joining", "fetch_zoho_button"]
    ordering = ("status",)
    actions = ['fetch_from_zoho_action']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Automatically trigger fetch on save
        try:
            fetch_details(obj.hrm_id)
        except Exception as e:
            logger.error(f"Auto-fetch failed for {obj.hrm_id}: {e}")

    def fetch_zoho_button(self, obj):
        if obj.id:
            return format_html(
                '<button type="submit" name="_fetch_zoho" class="button" style="background:#B800C4; color:white; border:none; padding:5px 15px; border-radius:4px; cursor:pointer;">Sync with Zoho Now</button>'
            )
        return "Save the payee first to enable sync"
    fetch_zoho_button.short_description = "Zoho Integration"

    @admin.action(description="Fetch details from Zoho")
    def fetch_from_zoho_action(self, request, queryset):
        success_count = 0
        error_count = 0
        for payee in queryset:
            try:
                # We call fetch_details directly since CELERY_TASK_ALWAYS_EAGER is True
                fetch_details(payee.hrm_id)
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Error fetching Zoho details for {payee.hrm_id}: {e}")
        
        if success_count:
            self.message_user(request, f"Successfully fetched details for {success_count} payees.")
        if error_count:
            self.message_user(request, f"Failed to fetch details for {error_count} payees. Check if Zoho tokens are configured.", messages.ERROR)

    def response_change(self, request, obj):
        if "_fetch_zoho" in request.POST:
            try:
                fetch_details(obj.hrm_id)
                self.message_user(request, "Successfully fetched details from Zoho.")
            except Exception as e:
                self.message_user(request, f"Error fetching from Zoho: {e}", messages.ERROR)
            return super().response_change(request, obj)
        return super().response_change(request, obj)

    def delete_queryset(self, request, queryset):
        queryset.update(is_deleted=True)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        qs = queryset.filter(is_deleted=False)

        if request.user.is_superuser:
            return restrict_queryset_by_group(qs, request.user)

        return restrict_queryset_by_group(qs, request.user)


class BankDetailsAdmin(admin.ModelAdmin):
    list_display = ["payee", "bank_name", "account_type",
                    "payee_acknowledgement", 'acknowledge_button']
    readonly_fields = ('payee_acknowledgement',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return restrict_queryset_by_group(qs, request.user,
                                          payee_field='payee')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Show the message only if the current user is in one of the restricted groups
        if request.user.groups.filter(name__in=RESTRICTED_PAYEE_GROUPS).exists():
            messages.info(
                request,
                "Please take a screenshot once you go through all of the bank details and acknowledge it."
            )
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def acknowledge_button(self, obj):
        if not obj.payee_acknowledgement:
            try:
                BankDetailsAck.objects.get(payee=obj.payee)
                return format_html(
                    '<a class="button" href="{}?payee={}">Acknowledge</a>',
                    reverse('admin:payees_bankdetailsack_change', args=[
                        BankDetailsAck.objects.get(payee=obj.payee).id]),
                    obj.payee.id
                )
            except BankDetailsAck.DoesNotExist:
                return format_html(
                    '<a class="button" href="{}?payee={}">Acknowledge</a>',
                    reverse('admin:payees_bankdetailsack_add'),
                    obj.payee.id
                )
        return "Acknowledged"

    acknowledge_button.short_description = 'Acknowledge'
    acknowledge_button.allow_tags = True


class BankDetailsAckAdmin(admin.ModelAdmin):
    list_display = ['payee', 'uploaded_date', 'is_approved']

    def get_readonly_fields(self, request, obj=None):
        # If superuser: no readonly fields
        if request.user.is_superuser:
            return []
        # Otherwise: make 'payee' readonly
        return ['payee']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return restrict_queryset_by_group(qs, request.user,
                                          payee_field='payee')

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if not request.user.is_superuser:
            try:
                initial['payee'] = Payee.objects.get(user=request.user).id
            except Payee.DoesNotExist:
                pass
        return initial

    def save_model(self, request, obj, form, change):
        # Auto-assign payee for non-superusers
        if not obj.payee_id and not request.user.is_superuser:
            try:
                obj.payee = Payee.objects.get(user=request.user)
            except Payee.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        # After saving, update payee_acknowledgement if approved
        if obj.is_approved:
            try:
                bank_details = BankDetails.objects.get(payee=obj.payee)
                if not bank_details.payee_acknowledgement:
                    bank_details.payee_acknowledgement = True
                    bank_details.save(update_fields=['payee_acknowledgement'])
            except BankDetails.DoesNotExist:
                pass

    def has_add_permission(self, request):
        # Superusers and HR can always add
        if request.user.is_superuser and not request.user.groups.filter(name__in=RESTRICTED_PAYEE_GROUPS).exists():
            return True

        # Get the payee object for the user
        try:
            payee = Payee.objects.get(user=request.user)
        except Payee.DoesNotExist:
            return False  # no payee, no permission

        # Check if a BankDetailAck already exists
        if BankDetailsAck.objects.filter(payee=payee).exists():
            return False

        return True  # allow add if no ack exists yet


admin.site.register(Payee, PayeeAdmin)
admin.site.register(BankDetails, BankDetailsAdmin)
admin.site.register(BankDetailsAck, BankDetailsAckAdmin)
