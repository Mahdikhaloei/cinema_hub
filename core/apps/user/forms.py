from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"
        field_classes = {"email": admin_forms.UsernameField}


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        fields = ("email",)
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }
        field_classes = {"email": admin_forms.UsernameField}
