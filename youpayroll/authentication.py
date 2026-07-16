from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from knox.auth import TokenAuthentication as KnoxTokenAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

_csrf_middleware = CsrfViewMiddleware(get_response=lambda request: None)

UNSAFE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


class CookieKnoxAuthentication(KnoxTokenAuthentication):
    """
    Knox token authentication that accepts the token from either:
    1. The Authorization header (primary — used by non-browser / GraphQL clients).
       No CSRF check needed because an attacker cannot set custom headers cross-site.
    2. The auth_token HttpOnly cookie (browser clients).
       CSRF is enforced for all unsafe HTTP methods when cookie auth is used.
    """

    def authenticate(self, request):
        # Try Authorization header first — explicit header means the caller is
        # not a passive browser, so no CSRF check required.
        result = super().authenticate(request)
        if result is not None:
            return result

        # Fall back to HttpOnly cookie
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        if not raw_token:
            return None

        # Enforce CSRF for unsafe methods when using cookie-based auth.
        if request.method in UNSAFE_METHODS:
            _csrf_middleware.process_request(request)
            reason = _csrf_middleware.process_view(request, None, (), {})
            if reason:
                raise PermissionDenied(f'CSRF validation failed: {getattr(reason, "reason_phrase", str(reason))}')

        prior_auth = request.META.get('HTTP_AUTHORIZATION')
        request.META['HTTP_AUTHORIZATION'] = f'Token {raw_token}'
        try:
            return super().authenticate(request)
        finally:
            if prior_auth is None:
                request.META.pop('HTTP_AUTHORIZATION', None)
            else:
                request.META['HTTP_AUTHORIZATION'] = prior_auth
