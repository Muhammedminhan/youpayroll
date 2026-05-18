from .models import Payee
from .constants import RESTRICTED_PAYEE_GROUPS
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError


def restrict_queryset_by_group(qs, user, payee_field=None):
    # If user is in restricted group, limit their access
    if user.groups.filter(name__in=RESTRICTED_PAYEE_GROUPS).exists():
        # Special case: if querying the User model directly
        if qs.model == get_user_model():
            return qs.filter(id=user.id)
        # Otherwise, restrict to related Payee or user field
        if payee_field:
            payee = Payee.objects.filter(user=user).first()
            if not payee:
                return qs.none()
            return qs.filter(**{payee_field: payee})
            
        # Fallback to user field check
        # Validate that the model has a user field to fail-fast cleanly
        opts = qs.model._meta
        try:
            opts.get_field('user')
        except Exception:
            raise FieldError(
                f"Model '{qs.model.__name__}' cannot be filtered automatically: "
                "payee_field was not specified and model has no 'user' field."
            )
        return qs.filter(user=user)

    # If not in restricted group, return all
    return qs
