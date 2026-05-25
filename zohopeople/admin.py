from django.contrib import admin
from .models import ZohoPeopleFormToken


@admin.register(ZohoPeopleFormToken)
class ZohoPeopleFormTokenAdmin(admin.ModelAdmin):
    """
    Admin view for ZohoPeopleFormToken.

    Access is restricted to superusers only. Token fields are hidden from
    add/change forms to prevent accidental exposure or modification through
    the admin UI.
    """
    readonly_fields = ('access_token', 'refresh_token', 'created', 'last_refreshed_at', 'singleton_lock')
    list_display = ('id', 'last_refreshed_at', 'created')
    # Exclude token fields from add/change forms to prevent mutations
    fields = ('last_refreshed_at', 'created', 'singleton_lock')

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False  # Tokens must only be updated via management command

    def has_add_permission(self, request):
        return False  # Tokens must only be created via management command

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
