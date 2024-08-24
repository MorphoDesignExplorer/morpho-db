from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from pydantic import BaseModel

import base64
import secrets

from authorization.totp import TOTP as TOTPGenerator

def generate_base32():
    secret = secrets.token_bytes(64)
    return base64.b32encode(secret).decode()


class TOTP(models.Model):
    class TOTPModel(BaseModel):
        secret: str

    user = models.OneToOneField(to=User, on_delete=models.CASCADE, primary_key=True)
    secret = models.TextField(verbose_name="TOTP_secret", unique=True, blank=False, default=generate_base32)

    def verify(self, unchecked_otp: str):
        totp_generator = TOTPGenerator(self.secret, 30, 6)
        return totp_generator.otp_now() == unchecked_otp


@receiver(post_save, sender=User)
def create_totp_object(sender, instance=None, created=False, **kwargs):
    if created:
        TOTP.objects.create(user=instance)
