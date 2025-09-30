# apps/users/utils.py
import requests
from django.conf import settings

def verify_turnstile_token(token: str) -> bool:
    """
    Verifies a Cloudflare Turnstile token.
    Returns True for a valid token, False otherwise.
    """
    if not token:
        return False

    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': settings.TURNSTILE_SECRET_KEY,
                'response': token,
            }
        )
        response.raise_for_status()
        result = response.json()
        return result.get('success', False)
    except requests.exceptions.RequestException:
        # If Cloudflare is down or the request fails, treat it as a failed validation
        return False