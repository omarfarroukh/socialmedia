from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from graphql_jwt.utils import jwt_decode
from django.contrib.auth import get_user_model
from django.utils.encoding import smart_str

User = get_user_model()

class GraphQLJWTAuthentication(BaseAuthentication):
    """
    DRF authentication class that validates GraphQL JWT tokens.
    Expects header: Authorization: JWT <token>
    """
    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth:
            return None
            
        auth = smart_str(auth)
        if not auth.startswith('JWT '):
            return None
            
        token = auth[4:]  # Remove 'JWT ' prefix
        
        try:
            payload = jwt_decode(token)
            username = payload.get('username')
            if not username:
                raise AuthenticationFailed('Invalid token')
                
            user = User.objects.get(**{User.USERNAME_FIELD: username})
            return (user, token)
            
        except Exception as e:
            raise AuthenticationFailed('Invalid or expired token')

    def authenticate_header(self, request):
        return 'JWT'