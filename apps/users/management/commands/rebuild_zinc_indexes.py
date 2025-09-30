# apps/users/management/commands/rebuild_zinc_index.py
import requests
from requests.auth import HTTPBasicAuth
from django.core.management.base import BaseCommand
from apps.users.models import Profile
import json

ZINC_HOST = "http://localhost:4080"
ZINC_USER = "admin"
ZINC_PASSWORD = "Admin@123"
INDEX_NAME = "profiles"

class Command(BaseCommand):
    help = 'Rebuilds the ZincSearch index for user profiles.'
    
    def handle(self, *args, **options):
        auth = HTTPBasicAuth(ZINC_USER, ZINC_PASSWORD)
        headers = {"Content-Type": "application/json"}

        self.stdout.write("Connecting to ZincSearch...")

        # Step 1: Delete old index (if it exists)
        self.stdout.write(f"Deleting old index '{INDEX_NAME}'...")
        delete_url = f"{ZINC_HOST}/api/index/{INDEX_NAME}"
        requests.delete(delete_url, auth=auth) # It's okay if this fails with a 404

        # Step 2: Create new index
        self.stdout.write(f"Creating new index '{INDEX_NAME}'...")
        create_url = f"{ZINC_HOST}/api/index"
        index_payload = {
            "name": INDEX_NAME,
            "storage_type": "disk"
        }
        response = requests.put(create_url, auth=auth, headers=headers, json=index_payload)
        response.raise_for_status() # Will fail if creation doesn't work

        # Step 3: Bulk insert documents
        self.stdout.write("Indexing profiles...")
        bulk_url = f"{ZINC_HOST}/api/_bulk"
        
        bulk_data = []
        for profile in Profile.objects.all().select_related('user'):
            bulk_data.append({
                "index": {
                    "_index": INDEX_NAME,
                    "_id": str(profile.id) # ID must be a string
                }
            })
            bulk_data.append({
                "user_id": profile.user.id,
                "username": profile.user.username,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "full_name": profile.full_name,
                "bio": profile.bio,
            })
            
        # ZincSearch's _bulk format needs newline-delimited JSON
        bulk_payload = "\n".join(json.dumps(item) for item in bulk_data) + "\n"

        response = requests.post(bulk_url, auth=auth, headers={"Content-Type": "application/json"}, data=bulk_payload)
        response.raise_for_status()

        self.stdout.write(self.style.SUCCESS(f"Successfully indexed {len(bulk_data) // 2} documents."))