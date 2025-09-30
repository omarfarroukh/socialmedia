from django.urls import path
from .views import AvatarUploadView

urlpatterns = [
    path('avatar/', AvatarUploadView.as_view(), name='avatar-upload'),
]