import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt
from django.conf import settings

logger = logging.getLogger(__name__)

class JWTAuthenticationMiddleware:
    

    def resolve(self, next, root, info, **kwargs):
        request = info.context
        auth_header = request.headers.get("Authorization", "")
        user = AnonymousUser()

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]
            try:
                # Decode token using the same method used for issuing tokens (PyJWT + SECRET_KEY)
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])  # raises on invalid/expired

                # Get user from token
                User = get_user_model()
                user_id = payload.get("user_id")
                user_obj = User.objects.filter(id=user_id).first()
                if user_obj:
                    user = user_obj
                    print(f"Authenticated user: {user.email}")
                    logger.info(f"Authenticated user: {user.email}")
                else:
                    print(f"No user found with id {user_id} from token.")
                    logger.warning(f"No user found with id {user_id} from token.")

            except jwt.ExpiredSignatureError:
                print("JWT token is invalid or expired.")
                logger.warning("JWT token is invalid or expired.")
            except (jwt.InvalidTokenError, InvalidToken, TokenError) as e:
                print(f"Invalid JWT token: {str(e)}")
                logger.warning(f"Invalid JWT token: {str(e)}")
            except Exception as e:
                print(f"Unexpected error decoding JWT: {str(e)}")
                logger.error(f"Unexpected error decoding JWT: {str(e)}")
        else:
            print("Authorization header missing or improperly formatted.")
            logger.info("Authorization header missing or improperly formatted.")

        request.user = user
        info.context.user = user
        return next(root, info, **kwargs)
