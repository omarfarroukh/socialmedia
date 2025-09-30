from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from .services import profile_update, validate_and_process_avatar
from .auth import GraphQLJWTAuthentication  # ← Import custom auth

class AvatarUploadView(APIView):
    authentication_classes = [GraphQLJWTAuthentication]  # ← Use custom auth
    permission_classes = []  # ← Remove IsAuthenticated, handle manually if needed
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Optional: manually check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        avatar_file = request.FILES.get('avatar')
        if not avatar_file:
            return Response(
                {"error": "No avatar file provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            processed_avatar = validate_and_process_avatar(avatar_file)
            profile = profile_update(
                profile=request.user.profile,
                avatar_file=processed_avatar
            )
            return Response({
                "avatar_url": profile.avatar.url if profile.avatar else None
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )