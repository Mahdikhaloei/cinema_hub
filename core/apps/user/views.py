from apps.user.forms.auth_forms import EmailForm, PasswordForm, RegisterForm
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import View
from django.views.generic.edit import CreateView, FormView

User = get_user_model()


class EmailVerificationView(FormView):
    template_name = "authentication/email_check.html"
    form_class = EmailForm
    success_url = reverse_lazy("auth:login")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        self.request.session["auth_email"] = email

        if User.objects.filter(email=email).exists():
            self.success_url = reverse_lazy("auth:login")
        else:
            self.success_url = reverse_lazy("auth:register")
        return super().form_valid(form)


class LoginView(FormView):
    template_name = "authentication/login_password.html"
    form_class = PasswordForm
    success_url = reverse_lazy("cinema:home")

    def form_valid(self, form):
        email = self.request.session.get("auth_email")
        password = form.cleaned_data["password"]

        user = authenticate(self.request, email=email, password=password)

        if user:
            login(self.request, user)
            return super().form_valid(form)
        else:
            form.add_error("password", _("Password is not correct!"))
            return self.form_invalid(form)


class RegisterUserView(CreateView):
    model = User
    form_class = RegisterForm
    template_name = "authentication/register_user.html"
    success_url = reverse_lazy("cinema:home")

    def form_valid(self, form):
        form.instance.email = self.request.session.get("auth_email")
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect(reverse_lazy("auth:auth_request"))
