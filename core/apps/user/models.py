from __future__ import annotations

from apps.user.managers import CustomUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.mixins.models import UUIDPrimaryKeyMixin


class UserRole(models.TextChoices):
    ADMIN = "admin", _("Admin")
    USER = "user", _("User")


class User(AbstractUser, UUIDPrimaryKeyMixin):
    """
    Default custom user model for CinemaHub.
    """
    # Due to this open issue of mypy, we ignore this error
    # https://github.com/typeddjango/django-stubs/issues/433
    username = None  # type: ignore
    email = models.EmailField(_("email address"), blank=True, unique=True)
    role = models.CharField(max_length=5, choices=UserRole.choices, default=UserRole.USER, verbose_name=_("role"))
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager() # type: ignore

    def __str__(self) -> str:
        return self.email
