from django.conf import settings
from knox.auth import TokenAuthentication as KnoxTokenAuthentication


class CookieKnoxAuthentication(KnoxTokenAuthentication):
    """
    Knox token authentication that accepts the token from either:
    1. The Authorization header (primary, used by non-browser clients / GraphQL)
    2. The auth_token HttpOnly cookie (primary for browser clients)
    """

    def authenticate(self, request):
        # Try Authorization header first
        result = super().authenticate(request)
        if result is not None:
            return result

        # Fall back to HttpOnly cookie
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        if not raw_token:
            return None

        # Reuse Knox's token validation by temporarily injecting into META
        request.META['HTTP_AUTHORIZATION'] = f'Token {raw_token}'
        try:
            return super().authenticate(request)
        finally:
            del request.META['HTTP_AUTHORIZATION']
