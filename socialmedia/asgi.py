import os
from django.core.asgi import get_asgi_application

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialmedia.settings')

# Import AFTER setting DJANGO_SETTINGS_MODULE
application = get_asgi_application()