from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

def otp_default():
    return uuid.uuid4().hex[:6].upper()

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

class Profile(models.Model):
    # Gender choices
    MALE = 'M'
    FEMALE = 'F'
    GENDER_CHOICES = [
        (MALE, 'Male'),
        (FEMALE, 'Female'),
    ]
    
    user = models.OneToOneField(
        'User', 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    
    # Personal info
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Social info
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    website = models.URLField(blank=True)
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Social relationships
    following = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='followers',
        blank=True
    )
    blocked_users = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='blocked_by',
        blank=True
    )

    def __str__(self):
        return f"{self.user.username}'s profile"
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.user.username

class UserOTP(models.Model):
    VERIFY = "V"
    RESET = "R"
    PURPOSES = [(VERIFY, "Email verify"), (RESET, "Password reset")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    purpose = models.CharField(max_length=1, choices=PURPOSES)
    token = models.CharField(max_length=6, default=otp_default)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "purpose")
        indexes = [models.Index(fields=["user", "purpose"])]

    def is_expired(self) -> bool:
        from django.utils import timezone
        return (timezone.now() - self.created).total_seconds() > 900  # 15 min