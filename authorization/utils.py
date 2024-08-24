import jwt

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import APIException, status
from authorization.serializers import Token
from django.core.cache import cache

from pydantic import BaseModel
from secrets import token_urlsafe
from datetime import datetime, timedelta, timezone

token_version = "0.3"


class ExpiredTokenException(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "token_expired"
    default_detail = "Token has expired."


class InvalidTokenException(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "token_invalid"
    default_detail = "Token is invalid."


class ResetPasswordSessionExpired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "reset_password_session_expired"
    default_detail = "Reset Password session has expired."


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        """
        Fetches the user object referenced by a JWT in the Bearer Token section.
        If the token is not verified, or something goes wrong, the operation fails.
        """
        try:
            token_string = get_authorization_header(request).decode().split()[1]
            token = Token.model_validate(jwt.decode(token_string, settings.SECRET_KEY, ["HS256"], options={"require": ["exp", "iat"]}))
            if token.verified:
                if token.version != token_version:
                    return None
                user = User.objects.get(username = token.username)
                return (user, None)
            else:
                return None

        except jwt.ExpiredSignatureError:
            return None
        except Exception:
            return None


class ResetPasswordSession(BaseModel):
    username: str
    key: str


def generate_reset_password_session(user: User) -> str:
    # first, get the user
    # register a randomly generated key in the cache in the format reset_password_%(username)
    # encode a jwt with the body {username: user.username, key: randomly_generated_key, exp: current time + 10 minutes} and sign it with the secret key.
    # return the jwt upwards

    cache_format = "reset_password_{username}"
    random_string = token_urlsafe(20)
    cache_key = cache_format.format(**{"username": user.username})

    if cache.get(cache_key) is not None:
        raise ResetPasswordSessionExpired()

    cache.set(cache_key, random_string, 60 * 10) # link expires in 10 minutes
    session = ResetPasswordSession(key=random_string, username=user.username)

    jwt_payload = {"exp": datetime.now(tz=timezone.utc) + timedelta(minutes=10), "iat": datetime.now(tz=timezone.utc), **session.model_dump()}
    webtoken = jwt.encode(jwt_payload, settings.SECRET_KEY, "HS256")
    return webtoken


def verify_reset_password_session(jwt_token_string: str) -> User | None:
    try:
        session = ResetPasswordSession.model_validate(
            jwt.decode(jwt_token_string, settings.SECRET_KEY, ["HS256"], options={"require": ["exp", "iat"]})
        )
        cache_key = "reset_password_{username}".format(username=session.username)
        session_key = cache.get(cache_key)
        if session_key is not None and session_key == session.key:
            user = User.objects.get(username = session.username)
            return user
        else:
            return None
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidSignatureError:
        return None
    except Exception as e:
        # other unknown errors
        return None


def delete_reset_password_session(jwt_token_string: str):
    try:
        session = ResetPasswordSession.model_validate(
            jwt.decode(jwt_token_string, settings.SECRET_KEY, ["HS256"], options={"require": ["exp", "iat"]})
        )
        cache_key = "reset_password_{username}".format(username=session.username)
        if cache.get(cache_key):
            cache.delete(cache_key)
    except:
        pass
