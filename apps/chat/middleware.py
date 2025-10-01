# apps/chat/middleware.py
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

@database_sync_to_async
def get_user_from_token(token_key):
    # IMPORT them here, inside the function
    from django.contrib.auth import get_user_model
    from graphql_jwt.utils import jwt_decode

    User = get_user_model()
    try:
        payload = jwt_decode(token_key)
        username = payload.get('username')
        user = User.objects.get(username=username)
        return user
    except (User.DoesNotExist, Exception):
        # It's better to explicitly return None on any failure
        return None

class JwtAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        # scope['user'] is traditionally an instance of AnonymousUser by default
        # We can import it here as it's a simple class, not a model
        from django.contrib.auth.models import AnonymousUser
        scope['user'] = AnonymousUser()

        if token:
            user = await get_user_from_token(token)
            if user:
                scope['user'] = user
        
        return await self.app(scope, receive, send)