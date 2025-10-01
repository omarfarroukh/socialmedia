from apps.users.models import User
from graphql_jwt.utils import jwt_decode
from strawberry.types import Info   # <-- NEW
from graphql_jwt.exceptions import JSONWebTokenError, PermissionDenied
import datetime
import uuid

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
    # convert any JWT problem into the code the Apollo link watches for
    raise PermissionDenied("UNAUTHENTICATED")




def timeuuid_to_datetime(timeuuid_obj: uuid.UUID) -> datetime.datetime:
    """Converts a Cassandra TimeUUID (version 1 UUID) to a Python datetime object."""
    # The timestamp is the number of 100-nanosecond intervals since
    # the Gregorian calendar reform (1582-10-15 00:00:00 UTC)
    uuid_timestamp = timeuuid_obj.time
    
    # We need to convert this to a Unix timestamp (seconds since 1970-01-01)
    # The difference between the UUID epoch and Unix epoch is 12219292800 seconds.
    unix_timestamp = (uuid_timestamp / 1e7) - 12219292800
    
    return datetime.datetime.fromtimestamp(unix_timestamp, tz=datetime.timezone.utc)