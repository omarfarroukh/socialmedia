import uuid
import datetime

def timeuuid_to_datetime(tuid: uuid.UUID) -> datetime.datetime:
    unix = (tuid.time / 1e7) - 12219292800
    return datetime.datetime.fromtimestamp(unix, tz=datetime.timezone.utc)