from typing import Tuple, Optional
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
import jwt


class GraphQLJWTAuthentication(BaseAuthentication):
    """
    DRF authentication backend that accepts the same Bearer token your GraphQL
    middleware (churchMember.User_Auth_middleware.JWTAuthenticationMiddleware) expects.

    It decodes the JWT using settings.SECRET_KEY and HS256 and extracts user_id.
    """

    keyword = "Bearer"

    def authenticate(self, request) -> Optional[Tuple[object, None]]:
        auth_header: str = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header or not auth_header.startswith(f"{self.keyword} "):
            return None

        token = auth_header.split(f"{self.keyword} ", 1)[1].strip()
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])  # same as GraphQL middleware
            user_id = payload.get("user_id")
            if not user_id:
                raise AuthenticationFailed("Invalid token: user_id missing")
            User = get_user_model()
            user = User.objects.filter(id=user_id).first()
            if not user:
                raise AuthenticationFailed("User not found")
            return (user, None)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")
