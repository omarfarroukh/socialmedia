# zinc_test.py
import requests
from requests.auth import HTTPBasicAuth

ZINC_HOST = "http://localhost:4080"
# Use your custom credentials here
ZINC_USER = "admin"
ZINC_PASSWORD = "Admin@123"

# We will test by listing the indexes, which is a core API function
url = f"{ZINC_HOST}/api/index"
auth = HTTPBasicAuth(ZINC_USER, ZINC_PASSWORD)

try:
    print(f"Sending GET request to {url}...")
    response = requests.get(url, auth=auth)

    # Raise an exception if the request failed (e.g., 401, 404, 500)
    response.raise_for_status()

    print("✅ Success! Connected to ZincSearch and authenticated.")
    print("Existing indexes:")
    print(response.json())

except requests.exceptions.RequestException as e:
    print(f"❌ Failed to connect to ZincSearch.")
    if e.response is not None:
        print(f"Status Code: {e.response.status_code}")
        print(f"Response: {e.response.text}")
    else:
        print(f"Error: {e}")