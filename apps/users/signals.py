from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile
from requests.auth import HTTPBasicAuth
import requests

User = get_user_model()


ZINC_HOST = "http://localhost:4080"
ZINC_USER = "admin"
ZINC_PASSWORD = "Admin@123"
INDEX_NAME = "profiles"
AUTH = HTTPBasicAuth(ZINC_USER, ZINC_PASSWORD)
HEADERS = {"Content-Type": "application/json"}







@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        
        
@receiver(post_save, sender=Profile)
def update_profile_document(sender, instance, **kwargs):
    """Creates or updates a profile document in ZincSearch."""
    doc = {
        "user_id": instance.user.id,
        "username": instance.user.username,
        "first_name": instance.first_name,
        "last_name": instance.last_name,
        "full_name": instance.full_name,
        "bio": instance.bio,
    }
    # ZincSearch uses PUT to create/update a document with a specific ID
    url = f"{ZINC_HOST}/api/{INDEX_NAME}/_doc/{instance.id}"
    requests.put(url, auth=AUTH, headers=HEADERS, json=doc)

@receiver(post_delete, sender=Profile)
def delete_profile_document(sender, instance, **kwargs):
    """Deletes a profile document from ZincSearch."""
    url = f"{ZINC_HOST}/api/{INDEX_NAME}/_doc/{instance.id}"
    requests.delete(url, auth=AUTH)

User = get_user_model()
@receiver(post_save, sender=User)
def update_user_in_profile_document(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        update_profile_document(sender=Profile, instance=instance.profile, **kwargs)
