from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
import os
import uuid
from datetime import date
from typing import Optional
from .models import UserOTP, Profile
from apps.graphql_api.types import UserType,ProfileType
from apps.users.tasks import send_mail_task
from django.core.exceptions import PermissionDenied
User = get_user_model()



def ensure_email_verified(user: User) -> None: #type: ignore
    """Raise error if user email is not verified."""
    if not user.is_email_verified:
        raise PermissionDenied("Email not verified")

# ---------- Business Logic Functions ----------
def calculate_age(date_of_birth: Optional[date]) -> Optional[int]:
    """Calculate age from date of birth."""
    if not date_of_birth:
        return None
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )

def get_full_name(first_name: str, last_name: str, username: str) -> str:
    """Get full name or fallback to username."""
    if first_name or last_name:
        return f"{first_name} {last_name}".strip()
    return username

def validate_and_process_avatar(uploaded_file) -> ContentFile:
    """Validate and process uploaded avatar."""
    if uploaded_file.size > 5 * 1024 * 1024:
        raise ValidationError("Avatar too large. Max 5MB.")
    
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError("Invalid file type. Use JPG, PNG, or GIF.")
    
    try:
        image = Image.open(uploaded_file)
        image.verify()
    except Exception:
        raise ValidationError("Invalid image file.")
    
    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    image.thumbnail((400, 400), Image.Resampling.LANCZOS)
    
    if image.mode in ('RGBA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        image = background
    
    output = BytesIO()
    image.save(output, format='JPEG', quality=85)
    output.seek(0)
    
    filename = f"avatar_{uuid.uuid4().hex}.jpg"
    return ContentFile(output.read(), name=filename)

# ---------- Profile Data Builders ----------
def build_profile_data(*, profile: Profile, current_user: Optional[User] = None, request=None) -> ProfileType: #type: ignore
    """Build complete profile data for API response."""
    age = calculate_age(profile.date_of_birth)
    full_name = get_full_name(profile.first_name, profile.last_name, profile.user.username)
    followers_count = profile.followers.count()
    following_count = profile.following.count()
    avatar_url = None
    if profile.avatar:
        if request:
            avatar_url = request.build_absolute_uri(profile.avatar.url)
        else:
            avatar_url = profile.avatar.url  # fallback    
    # Check if current user is following this profile
    is_following = False
    if current_user and current_user != profile.user:
        is_following = current_user.profile.following.filter(id=profile.id).exists()
    
    
    return ProfileType(
        id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        country=profile.country,
        bio=profile.bio,
        website=profile.website,
        is_private=profile.is_private,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        avatar_url=avatar_url,
        age=age,
        full_name=full_name,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following,
        user=profile.user
    )

def build_user_data(*, user: User, current_user: Optional[User] = None, request=None) -> UserType:# type: ignore
    """Build complete user data for API response."""
    profile_data = build_profile_data(profile=user.profile, current_user=current_user, request=request)
    return UserType(
        id=user.id,
        username=user.username,
        email=user.email,
        is_email_verified=user.is_email_verified,   
        profile=profile_data,
    )

# ---------- User creation ----------
@transaction.atomic
def user_create(*, username: str, email: str, password: str) -> User: # type: ignore
    if User.objects.filter(username=username).exists():
        raise ValidationError("Username taken")
    if User.objects.filter(email=email).exists():
        raise ValidationError("Email taken")
    user = User(username=username, email=email)
    user.set_password(password)
    user.full_clean()
    user.save()
    # Profile auto-created by signal
    
    UserOTP.objects.create(user=user, purpose=UserOTP.VERIFY)
    send_verification_email(user)
    return user

# ---------- OTP helpers ----------
def _send_templated_email(user: User, subject: str, template_base: str, ctx: dict): # type: ignore
    html_message = render_to_string(f"users/{template_base}.html", ctx)
    plain_message = render_to_string(f"users/{template_base}.txt", ctx)
    send_mail_task.delay(
        subject,
        plain_message,
        [user.email],
        html_message=html_message
    )

def send_verification_email(user: User) -> None: # type: ignore
    otp = UserOTP.objects.get(user=user, purpose=UserOTP.VERIFY)
    _send_templated_email(
        user,
        "Verify your account",
        "email_verify",
        {"username": user.username, "code": otp.token}
    )

def send_password_reset_email(user: User) -> None: # type: ignore   
    otp, _ = UserOTP.objects.get_or_create(
        user=user, purpose=UserOTP.RESET,
        defaults={"token": UserOTP._meta.get_field("token").default()}
    )
    _send_templated_email(
        user,
        "Password reset",
        "password_reset",
        {"username": user.username, "code": otp.token}
    )

def user_resend_verification_email(*, email: str) -> bool:
    """Resend verification email (creates new OTP)."""
    user = User.objects.filter(email=email).first()
    if not user:
        # Silent fail (don't reveal if email exists)
        return False
        
    if user.is_email_verified:
        raise ValidationError("Email already verified")
    
    # Delete old OTP and create new one
    UserOTP.objects.filter(user=user, purpose=UserOTP.VERIFY).delete()
    UserOTP.objects.create(user=user, purpose=UserOTP.VERIFY)
    send_verification_email(user)
    return True

# ---------- Email verification ----------
def user_verify_email(*, username: str, code: str) -> User: # type: ignore
    try:
        otp = UserOTP.objects.select_related("user").get(
            user__username=username, purpose=UserOTP.VERIFY, token=code.upper()
        )
    except UserOTP.DoesNotExist:
        raise ValidationError("Invalid or expired code")
    if otp.is_expired():
        raise ValidationError("Code expired")
    user = otp.user
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    otp.delete()
    return user

# ---------- Password reset ----------
def user_reset_password_request(*, email: str) -> str:
    user = User.objects.filter(email=email).first()
    if user:
        send_password_reset_email(user)
    return user.username if user else ""

def user_reset_password_confirm(*, username: str, code: str, new_password: str) -> bool:
    try:
        otp = UserOTP.objects.select_related("user").get(
            user__username=username, purpose=UserOTP.RESET, token=code.upper()
        )
    except UserOTP.DoesNotExist:
        raise ValidationError("Invalid or expired code")
    if otp.is_expired():
        raise ValidationError("Code expired")
    user = otp.user
    user.set_password(new_password)
    user.save(update_fields=["password"])
    otp.delete()
    return True

# ---------- Authenticated password change ----------
def user_set_password(*, user: User, current_password: str, new_password: str) -> bool: # type: ignore
    if not user.check_password(current_password):
        raise ValidationError("Current password is incorrect")
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return True

# ---------- Profile updates ----------
def profile_update(
    *, 
    profile: Profile, 
    first_name: str = None,
    last_name: str = None,
    date_of_birth: date = None,
    gender: str = None,
    country: str = None,
    bio: str = None, 
    website: str = None, 
    is_private: bool = None, 
    avatar_file=None
) -> Profile:
    """Update profile with optional fields."""
    if first_name is not None:
        profile.first_name = first_name
    if last_name is not None:
        profile.last_name = last_name
    if date_of_birth is not None:
        profile.date_of_birth = date_of_birth
    if gender is not None:
        if gender not in dict(Profile.GENDER_CHOICES):
            raise ValidationError("Invalid gender choice")
        profile.gender = gender
    if country is not None:
        profile.country = country
    if bio is not None:
        profile.bio = bio
    if website is not None:
        profile.website = website
    if is_private is not None:
        profile.is_private = is_private
    
    if avatar_file:
        processed_avatar = validate_and_process_avatar(avatar_file)
        profile.avatar.save(processed_avatar.name, processed_avatar, save=False)
    
    profile.save()
    return profile

# ---------- Follow/Unfollow ----------
def profile_follow(*, follower_profile: Profile, followee_profile: Profile) -> bool:
    if follower_profile.user == followee_profile.user:
        raise ValidationError("Cannot follow yourself")
    follower_profile.following.add(followee_profile)
    return True

def profile_unfollow(*, follower_profile: Profile, followee_profile: Profile) -> bool:
    follower_profile.following.remove(followee_profile)
    return True

# ---------- Block/Unblock ----------
def profile_block(*, blocker_profile: Profile, blocked_profile: Profile) -> bool:
    if blocker_profile.user == blocked_profile.user:
        raise ValidationError("Cannot block yourself")
    blocker_profile.blocked_users.add(blocked_profile)
    blocker_profile.following.remove(blocked_profile)
    blocked_profile.following.remove(blocker_profile)
    return True

def profile_unblock(*, blocker_profile: Profile, blocked_profile: Profile) -> bool:
    blocker_profile.blocked_users.remove(blocked_profile)
    return True