from __future__ import annotations
import requests
import strawberry
from strawberry.types import Info
from strawberry.exceptions import GraphQLError
from strawberry.file_uploads import Upload
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from graphql_jwt.shortcuts import get_token
from apps.graphql_api.utils import get_user
from apps.users.models import Profile
from apps.users.services import (
    ensure_email_verified, user_create, user_resend_verification_email, user_reset_password_confirm, user_reset_password_request,
    user_set_password, user_verify_email, profile_update, profile_follow,
    profile_unfollow, profile_block, profile_unblock,
    build_user_data, build_profile_data
)
from graphql_jwt.utils import jwt_decode
from django.contrib.auth import get_user_model
from graphql_jwt.refresh_token.models import RefreshToken
from graphql_jwt.exceptions import PermissionDenied
from typing import Optional
from datetime import datetime, date
from typing import List
from requests.auth import HTTPBasicAuth
from apps.users.utils import verify_turnstile_token # 👈 Import the function
from .types import UserType, ProfileType, AuthPayload, AuthSuccess, AuthRequiresVerification, RefreshPayload, VerifyEmailPayload
User = get_user_model()


# ---------- Inputs ----------
@strawberry.input
class RegisterInput:
    username: str
    email: str
    password: str
    captcha_token: str # 👈 New field


@strawberry.input
class TokenInput:
    username: str
    password: str

@strawberry.input
class RefreshInput:
    refresh: str

@strawberry.input
class VerifyEmailInput:
    username: str
    code: str

@strawberry.input
class ResetPasswordRequestInput:
    email: str

@strawberry.input
class ResetPasswordConfirmInput:
    username: str
    code: str
    new_password: str
    
@strawberry.input
class ResendVerificationInput:
    email: str

@strawberry.input
class SetPasswordInput:
    current_password: str
    new_password: str

@strawberry.input
class UpdateProfileInput:
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    is_private: Optional[bool] = None
    avatar: Optional[Upload] = None  #type: ignore

@strawberry.input
class TargetUserInput:
    username: str
    
# ---------- Mutations ----------
@strawberry.type
class Mutation:
    @strawberry.mutation
    def register(self, data: RegisterInput) -> UserType:
        
        is_captcha_valid = verify_turnstile_token(data.captcha_token)
        if not is_captcha_valid:
            raise GraphQLError("Invalid CAPTCHA. Please try again.")
        
        try:
            user = user_create(
                username=data.username,
                email=data.email,
                password=data.password,
            )
            # Build user data with no current user (since just registered)
            user_data = build_user_data(user=user, current_user=None)
            return user_data
        except ValidationError as e:
            raise GraphQLError(str(e))

    @strawberry.mutation
    def token_auth(self, info: Info, data: TokenInput) -> AuthPayload:   #type: ignore
        user = authenticate(username=data.username, password=data.password)
        if user is None:
            raise GraphQLError("Invalid credentials")

        if not user.is_email_verified:
            return AuthRequiresVerification(email=user.email)

        access = get_token(user)
        refresh_obj = RefreshToken.objects.create(user=user)
        return AuthSuccess(
            access=access,
            refresh=refresh_obj.token,
            user=build_user_data(user=user, current_user=user),
        )
        
    @strawberry.mutation
    def refresh_token(self, info: Info, data: RefreshInput) -> RefreshPayload:
        try:
            # Get refresh token from DB
            refresh_token = RefreshToken.objects.select_related('user').get(
                token=data.refresh
            )
            
            if refresh_token.is_expired():
                raise GraphQLError("Refresh token expired")
            
            user = refresh_token.user
            
            # Revoke old token
            refresh_token.revoke()
            
            # Create new tokens
            access = get_token(user)
            new_refresh_token = RefreshToken.objects.create(user=user)
            
            # Build user data
            user_data = build_user_data(user=user, current_user=user)
            
            return RefreshPayload(
                access=access,
                refresh=new_refresh_token.token,
                user=user_data
            )
            
        except ObjectDoesNotExist:
            raise GraphQLError("Invalid refresh token")
        except Exception as e:
            raise GraphQLError(f"Refresh failed: {str(e)}")

    @strawberry.mutation
    def verify_email(self, data: VerifyEmailInput) -> VerifyEmailPayload:
        try:
            # Modify the service to return the user object on success
            user = user_verify_email(username=data.username, code=data.code)
            
            # If user_verify_email returns a user, it means success.
            # Now, we generate tokens for them, just like in token_auth.
            access = get_token(user)
            refresh_obj = RefreshToken.objects.create(user=user)
            refresh = refresh_obj.token
            
            # Build and return the full payload
            user_data = build_user_data(user=user, current_user=user)
            return VerifyEmailPayload(access=access, refresh=refresh, user=user_data)
            
        except ValidationError as e:
            raise GraphQLError(str(e))

    @strawberry.mutation
    def resend_verification_email(self, data: ResendVerificationInput) -> bool:
        try:
            # This calls the service function you already wrote
            return user_resend_verification_email(email=data.email)
        except ValidationError as e:
            raise GraphQLError(str(e))

    @strawberry.mutation
    def reset_password_request(self, data: ResetPasswordRequestInput) -> str:
        return user_reset_password_request(email=data.email)

    @strawberry.mutation
    def reset_password_confirm(self, data: ResetPasswordConfirmInput) -> bool:
        try:
            return user_reset_password_confirm(
                username=data.username,
                code=data.code,
                new_password=data.new_password,
            )
        except ValidationError as e:
            raise GraphQLError(str(e))

    @strawberry.mutation
    def set_password(self, info: Info, data: SetPasswordInput) -> bool:
        user = get_user(info)
        if user is None:
            raise PermissionDenied("UNAUTHENTICATED")
        
        ensure_email_verified(user)

        try:
            return user_set_password(
                user=user,
                current_password=data.current_password,
                new_password=data.new_password,
            )
        except ValidationError as e:
            raise GraphQLError(str(e))

    @strawberry.mutation
    def update_profile(self, info: Info, data: UpdateProfileInput) -> ProfileType:
        user = get_user(info)
        if not user:
            raise PermissionDenied("UNAUTHENTICATED")
        
        ensure_email_verified(user)

        try:
            profile = profile_update(
                profile=user.profile,
                first_name=data.first_name,
                last_name=data.last_name,
                date_of_birth=data.date_of_birth,
                gender=data.gender,
                country=data.country,
                bio=data.bio,
                website=data.website,
                is_private=data.is_private,
                avatar_file=data.avatar
            )
            profile_data = build_profile_data(profile=profile, current_user=user)
            return profile_data
        except ValidationError as e:
            raise GraphQLError(str(e))

    @strawberry.mutation
    def follow(self, info: Info, data: TargetUserInput) -> bool:
        user = get_user(info)
        if not user:
            raise PermissionDenied("UNAUTHENTICATED")
        
        ensure_email_verified(user)

        try:
            target_user = User.objects.get(username=data.username)
            return profile_follow(
                follower_profile=user.profile,
                followee_profile=target_user.profile
            )
        except ObjectDoesNotExist:
            raise GraphQLError("User not found")
        except ValidationError as e:
            raise GraphQLError(str(e))

    @strawberry.mutation
    def unfollow(self, info: Info, data: TargetUserInput) -> bool:
        user = get_user(info)
        if not user:
            raise PermissionDenied("UNAUTHENTICATED")
        
        ensure_email_verified(user)

        try:
            target_user = User.objects.get(username=data.username)
            return profile_unfollow(
                follower_profile=user.profile,
                followee_profile=target_user.profile
            )
        except ObjectDoesNotExist:
            raise GraphQLError("User not found")

    @strawberry.mutation
    def block(self, info: Info, data: TargetUserInput) -> bool:
        user = get_user(info)
        if not user:
            raise PermissionDenied("UNAUTHENTICATED")
        
        ensure_email_verified(user)
        
        try:
            target_user = User.objects.get(username=data.username)
            return profile_block(
                blocker_profile=user.profile,
                blocked_profile=target_user.profile
            )
        except ObjectDoesNotExist:
            raise GraphQLError("User not found")
        except ValidationError as e:
            raise GraphQLError(str(e))

    @strawberry.mutation
    def unblock(self, info: Info, data: TargetUserInput) -> bool:
        user = get_user(info)
        if not user:
            raise PermissionDenied("UNAUTHENTICATED")
        
        ensure_email_verified(user)
        
        try:
            target_user = User.objects.get(username=data.username)
            return profile_unblock(
                blocker_profile=user.profile,
                blocked_profile=target_user.profile
            )
        except ObjectDoesNotExist:
            raise GraphQLError("User not found")

# ---------- Queries ----------
@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: Info) -> Optional[UserType]:
        request = info.context.request
        auth = request.headers.get("authorization", "")
        if not auth.startswith("JWT "):
            raise PermissionDenied("UNAUTHENTICATED")
        token = auth[4:]
        try:
            payload = jwt_decode(token)
            user = User.objects.select_related('profile').get(
                **{User.USERNAME_FIELD: payload["username"]}
            )
            user_data =  build_user_data(user=user, current_user=user, request=info.context.request)
            return user_data
        except Exception:
            raise PermissionDenied("UNAUTHENTICATED")
    
    @strawberry.field
    def profile(self, info: Info, username: str) -> Optional[ProfileType]:
        try:
            target_user = User.objects.select_related('profile').get(username=username)
            current_user = get_user(info)  # may be None

            if current_user and current_user.profile.blocked_users.filter(id=target_user.profile.id).exists():
                raise PermissionDenied("You have blocked this user")
            
            # ---- Block check ----
            if current_user and target_user.profile.blocked_users.filter(id=current_user.profile.id).exists():
                raise PermissionDenied("You are blocked from viewing this profile")

            # ---- Privacy check (existing) ----
            if target_user.profile.is_private and current_user != target_user:
                is_following = (
                    current_user.profile.following.filter(id=target_user.profile.id).exists()
                    if current_user else False
                )
                if not is_following:
                    raise PermissionDenied("Profile is private")

            profile_data = build_profile_data(
                profile=target_user.profile,
                current_user=current_user,
                request=info.context.request
            )
            return profile_data

        except ObjectDoesNotExist:
            raise GraphQLError("User not found")
        
    @strawberry.field
    def search_profiles(self, info: Info, query: str) -> List[ProfileType]:
        # --- Part 1: Get the current user ---
        current_user = get_user(info)
        
        # --- Part 2: The ZincSearch Query (remains the same) ---
        if not query or len(query.strip()) < 2:
            return []

        url = f"http://localhost:4080/api/profiles/_search"
        auth = HTTPBasicAuth("admin", "Admin@123")
        
        search_payload = {
                "query": {
                    "query_string": {
                        "query": f"{query}*", # e.g., "oma" becomes "oma*"
                        "fields": ["username", "first_name", "last_name", "full_name", "bio"]
                    }
                },
                "size": 20,
                "_source": ["user_id"]
            }
        response = requests.post(url, auth=auth, json=search_payload)
        response.raise_for_status()
        
        results = response.json()
        hit_ids = [hit['_source']['user_id'] for hit in results.get('hits', {}).get('hits', [])]

        if not hit_ids:
            return []

        # --- Part 3: Exclude the current user ---
        # THE KEY CHANGE IS HERE:
        # If the current user is logged in, remove their ID from the list.
        if current_user and current_user.id in hit_ids:
            hit_ids.remove(current_user.id)
        
        # --- Part 4: Fetch Profiles from PostgreSQL (remains the same) ---
        profiles = Profile.objects.filter(user_id__in=hit_ids).select_related('user')
        
        profiles_dict = {profile.user_id: profile for profile in profiles}
        ordered_profiles = [profiles_dict[id] for id in hit_ids if id in profiles_dict]

        # --- Part 5: Build and return the response (remains the same) ---
        return [build_profile_data(profile=p, current_user=current_user) for p in ordered_profiles]
    
schema = strawberry.Schema(query=Query, mutation=Mutation)