from __future__ import annotations
import strawberry
from typing import Optional, List
from datetime import datetime, date

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
    created_at: datetime
    updated_at: datetime
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