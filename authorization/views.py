import jwt
import regex

from datetime import datetime, timezone, timedelta
from authorization.models import TOTP, generate_base32
from authorization.serializers import Token
from authorization.utils import token_version, JWTAuthentication, generate_reset_password_session, verify_reset_password_session, delete_reset_password_session
from django.contrib.auth.models import User
from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails

from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings


# Figure out throttling for later. Must throttle for a day on 10 failed requests in 10 minutes.


class AuthInitView(APIView):
    """
    Accepts a set of user credentials and generates an unverified JWT.
    This token has a short lifetime, and needs to be verified through a TOTP.

    Raises APIException on failure at any stage.
    """

    class InitRequest(BaseModel):
        username: str
        password: str

    def post(self, request: Request, *args, **kwargs):
        try:
            form = self.InitRequest.model_validate(request.data)
        except ValidationError as ve:
            errors: ErrorDetails = ve.errors()
            return Response(errors)
        except Exception as e:
            raise APIException("Malformed request body.")


        try:
            user = User.objects.get(username=form.username)
        except:
            raise APIException("User not found.")


        if user.check_password(form.password):
            unverified_token = Token(username=user.username, verified=False, version=token_version)
            webtoken = jwt.encode({
                "iat": datetime.now(tz=timezone.utc),
                "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=10),
                **unverified_token.model_dump()
            }, settings.SECRET_KEY, "HS256")
            return Response(
                {"token": webtoken, "secret": TOTP.objects.get(user=user).secret}
            )
        else:
            raise APIException("Invalid credentials.")


class AuthVerifyView(APIView):
    """
    Accepts an unverified JWT with an OTP and generates a verified JWT if the user's generated TOTP matches with the submitted OTP.

    raises APIException on failure at any stage.
    """

    class VerifyRequest(BaseModel):
        otp: str

    def post(self, request: Request, *args, **kwargs):
        try:
            token_string = get_authorization_header(request).decode().split()[1]
            token = Token.model_validate(jwt.decode(token_string, settings.SECRET_KEY, ["HS256"], options={"require": ["exp", "iat"]}))
        except Exception as e:
            raise APIException("Invalid Authorization Token." + repr(e) + token_string)


        try:
            form = self.VerifyRequest.model_validate(request.data)
        except:
            raise APIException("Invalid body. Body must be of JSON form and contain only one field: otp.")


        try:
            otp_object = TOTP.objects.get(user__username=token.username)
        except:
            raise APIException("User not found.")


        if otp_object.verify(form.otp):
            token.verified = True
            webtoken = jwt.encode({
                "iat": datetime.now(tz=timezone.utc),
                "exp": datetime.now(tz=timezone.utc) + timedelta(days=31),
                **token.model_dump()
            }, settings.SECRET_KEY, "HS256")
            return Response({"token": webtoken})
        else:
            raise APIException("invalid OTP.")


class AuthRefreshSecretView(APIView):
    """
    Replaces the Base32 secret on a TOTP model with a new one. Use with care.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    class RefreshSecretRequest(BaseModel):
        otp: str

    def post(self, request: Request, *args, **kwargs):
        try:
            form = self.RefreshSecretRequest.model_validate(request.data)
        except:
            raise APIException("Invalid body. Body must be of JSON form and contain only one field: otp.")
        
        try:
            otp_object = TOTP.objects.get(user=request.user)
        except:
            raise APIException("User's TOTP device not found.")

        if otp_object.verify(form.otp):
            otp_object.secret = generate_base32()
            otp_object.save()
            return Response("secret was replaced.")
        else:
            raise APIException("invalid OTP.")


class AuthInitiateResetPasswordView(APIView):
    """
    Initiates a reset password session and sends an email to the 'user' initiating.
    """

    def get(self, request: Request, *args, **kwargs):
        try:
            # this identity could be a username or email. Send an email to the concerened user either way.
            ident = request.query_params.get("ident")
            if regex.search(r"^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$", ident):
                # is an email
                user = User.objects.get(email=ident)
            else:
                user = User.objects.get(username=ident)
            print(user)
            token = generate_reset_password_session(user)
            link = f"/forgot_password?session={token}"
            # user.email_user("[Morpho Design Explorer] Reset Password Request", "We received a request to reset your password. Here's the link: {link}. <br/> If this wasn't you, ignore this email. <br/><br/>Admin,<br/>Morpho Design Explorer".format(**{"link": link}))
            # Print this link during development.
            print("link: ", link)
        except Exception as e:
            pass
        # this endpoint must behave uniformly regardless of whether the operation succeeded or not.
        # check OWASP Forgot Password requirements.
        return Response({"detail": "success"})


class AuthResetPasswordView(APIView):
    """
    Resets the password for a user if the reset password session hasn't expired.
    """

    class ResetPasswordRequest(BaseModel):
        session: str
        replacement_password: str

    def post(self, request: Request, *args, **kwargs):
        try:
            form = self.ResetPasswordRequest.model_validate(request.data)
            user = verify_reset_password_session(form.session)
            if user:
                if user.check_password(form.replacement_password):
                    raise APIException("replacement password is the same as the present password.", code="reset_password_too_similar")
                else:
                    user.set_password(form.replacement_password)
                    user.save()
                    delete_reset_password_session(form.session)
                    return Response({"status": "success"})
            else:
                raise APIException("Reset Password Session is invalid or has expired.")
        except jwt.ExpiredSignatureError or jwt.InvalidSignatureError:
            raise APIException("Reset Password Session is invalid or has expired.")
