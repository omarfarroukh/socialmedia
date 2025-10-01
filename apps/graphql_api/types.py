from __future__ import annotations
import strawberry
import datetime
from typing import Optional, List
from datetime import  date
from strawberry.types import Info
from django.contrib.auth import get_user_model
from apps.users.models import Profile
from apps.chat.models import Conversation, ConversationParticipant

User = get_user_model()

# Foward declare the dependent type with a string to avoid order-of-definition issues
@strawberry.type
class ProfileType:
    id: int
    first_name: str
    last_name: str
    date_of_birth: Optional[date]
    gender: Optional[str]
    country: str
    bio: str
    website: str
    is_private: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    avatar_url: Optional[str]
    age: Optional[int]
    full_name: str
    followers_count: int
    following_count: int
    is_following: bool
    user: "UserType"  # Use forward reference as a string

@strawberry.type
class UserType:
    id: int
    username: str
    email: str
    is_email_verified: bool
    profile: ProfileType

# All other API-specific types also go here
@strawberry.type
class AuthSuccess:
    access: str
    refresh: str
    user: UserType

@strawberry.type
class AuthRequiresVerification:
    email: str
    message: str = "Email not verified. Please check your inbox."

AuthPayload = strawberry.union("AuthPayload", (AuthSuccess, AuthRequiresVerification))

@strawberry.type
class RefreshPayload:
    access: str
    refresh: str
    user: UserType

@strawberry.type
class VerifyEmailPayload:
    access: str
    refresh: str
    user: UserType
    
    
@strawberry.type
class ConversationParticipantType:
    username: str
    avatar_url: Optional[str]
    last_read_timestamp: Optional[datetime.datetime]

    @classmethod
    def from_instance(cls, participant_obj: ConversationParticipant):
        # This now takes the intermediary 'ConversationParticipant' object
        if participant_obj.user.profile and participant_obj.user.profile.avatar:
            avatar_url = participant_obj.user.profile.avatar.url
        else:
            avatar_url = None
        
        return cls(
            username=participant_obj.user.username,
            avatar_url=avatar_url,
            last_read_timestamp=participant_obj.last_read_timestamp
        )
        
@strawberry.type
class ConversationType:
    id: strawberry.ID
    last_message_at: Optional[datetime.datetime]
    participants: List[ConversationParticipantType]

    @strawberry.field
    def participants(self, info: Info) -> List[ConversationParticipantType]:
        # Fetch the 'through' model objects which contain the read timestamp
        participant_objects = self.conversationparticipant_set.all().select_related('user', 'user__profile')
        return [ConversationParticipantType.from_instance(p) for p in participant_objects]

@strawberry.type
class MessageType:
    author_username: str
    content: str
    timestamp: str