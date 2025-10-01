import uuid
from typing import List
from django.db.models import Count
from django.contrib.auth import get_user_model
from strawberry.types import Info
from graphql_jwt.exceptions import PermissionDenied
from graphql import GraphQLError

from apps.chat.models import Conversation, ConversationParticipant
from apps.chat.cassandra import cassandra_session  # see note below
from apps.chat.utils import timeuuid_to_datetime  # see note below
from apps.graphql_api.utils import get_user
User = get_user_model()

# ---------- public API ----------
def start_conversation(info: Info, participant_username: str) -> Conversation:
    """
    Idempotent conversation starter.
    Returns the *existing* 2-person conversation if one already exists,
    otherwise creates it.
    """
    user = get_user(info)

    # 1. Other user must exist
    try:
        other = User.objects.get(username=participant_username)
    except User.DoesNotExist:
        raise GraphQLError("The user you are trying to message does not exist.")

    # 2. No self-talk
    if user.id == other.id:
        raise GraphQLError("You cannot start a conversation with yourself.")

    # 3. Idempotency: conversation with exactly these two users
    existing = (
        Conversation.objects
        .annotate(p_count=Count("participants"))
        .filter(p_count=2)
        .filter(participants=user)
        .filter(participants=other)
        .distinct()
        .first()
    )
    print(f"[start_conversation] existing conversation = {existing}")
    if existing:
        return existing
    
    # 4. Create new conversation
    conv = Conversation.objects.create()
    ConversationParticipant.objects.bulk_create(
        [
            ConversationParticipant(user=user, conversation=conv),
            ConversationParticipant(user=other, conversation=conv),
        ]
    )
    return conv


def list_conversations(info: Info) -> List[Conversation]:
    user = get_user(info)
    return list(user.conversations.all().order_by("-last_message_at"))


def list_messages(info: Info, conversation_id: str, limit: int = 50) -> List["MessageType"]:  #type: ignore
    """
    Returns a list of MessageType *dataclass* instances (not ORM models).
    MessageType is assumed to be defined in schema.py
    """
    from apps.graphql_api.types import MessageType  # avoid circular import

    user = get_user(info)
    conv_uuid = uuid.UUID(conversation_id)

    rows = cassandra_session.execute(
        """
        SELECT author_username, content, timestamp
        FROM   messages
        WHERE  conversation_id = %s
        LIMIT  %s
        """,
        (conv_uuid, limit),
    )

    return [
        MessageType(
            author_username=row.author_username,
            content=row.content,
            timestamp=timeuuid_to_datetime(row.timestamp).isoformat(),
        )
        for row in rows
    ]