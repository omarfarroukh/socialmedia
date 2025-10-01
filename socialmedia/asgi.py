# socialmedia/asgi.py
import os
from django.core.asgi import get_asgi_application

# --- Step 1: Set the default settings module ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialmedia.settings')

# --- Step 2: Initialize the Django application registry ---
# This line is crucial. It loads all the apps and models.
django_asgi_app = get_asgi_application()

# --- Step 3: Now that Django is loaded, we can safely import Channels and our routing ---
from channels.routing import ProtocolTypeRouter, URLRouter
from apps.chat.middleware import JwtAuthMiddleware
import apps.chat.routing

application = ProtocolTypeRouter({
    # The HTTP protocol handler uses the Django app we just initialized.
    "http": django_asgi_app,
    
    # The WebSocket protocol handler
    "websocket": JwtAuthMiddleware(
        URLRouter(
            apps.chat.routing.websocket_urlpatterns
        )
    ),
})