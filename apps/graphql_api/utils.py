from apps.users.models import User
from graphql_jwt.utils import jwt_decode
from strawberry.types import Info   # <-- NEW
from graphql_jwt.exceptions import JSONWebTokenError, PermissionDenied

def get_user(info: Info) -> User | None: 
    request = info.context.request
    auth = request.headers.get("authorization", "")
    if not auth.startswith("JWT "):
        return None
    token = auth[4:]
    try:
        payload = jwt_decode(token)
        return User.objects.get(**{User.USERNAME_FIELD: payload["username"]})
    except Exception:
        return None
    
def jwt_error_handler(error, context):
    print('>>> JWT error, raising UNAUTHENTICATED')  # ← should appear in runserver console

    # convert any JWT problem into the code the Apollo link watches for
    raise PermissionDenied("UNAUTHENTICATED")