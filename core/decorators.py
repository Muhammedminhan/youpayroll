from graphql import GraphQLError


def login_required(func):
    def wrapper(self, info, *args, **kwargs):
        user = info.context.user  # Access user from request context
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")
        return func(self, info, *args, **kwargs)

    return wrapper
