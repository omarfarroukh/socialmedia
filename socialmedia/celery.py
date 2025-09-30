import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "socialmedia.settings")

app = Celery("socialmedia")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()          # auto-find tasks.py in every app