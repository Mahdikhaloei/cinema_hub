from apps.user.tests.factories import UserFactory
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class EmailVerificationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.valid_email = "test@example.com"
        self.invalid_email = "nonexistent@example.com"
        self.user = User.objects.create_user(
            email=self.valid_email, password="validpassword123" # noqa: S106
        )
        self.url = reverse("auth:auth_request")

    def test_email_verification_form_valid_user(self):
        form_data = {"email": self.valid_email}
        response = self.client.post(self.url, data=form_data)
        self.assertRedirects(response, reverse("auth:login"))
        self.assertEqual(self.client.session.get("auth_email"), self.valid_email)

    def test_email_verification_form_invalid_user(self):
        form_data = {"email": self.invalid_email}
        response = self.client.post(self.url, data=form_data)
        self.assertRedirects(response, reverse("auth:register"))
        self.assertEqual(self.client.session.get("auth_email"), self.invalid_email)

    def test_email_verification_view_renders_correct_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "authentication/email_check.html")


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.valid_email = "test@example.com"
        self.valid_password = "validpassword123" # noqa: S105
        self.invalid_password = "wrongpassword" # noqa: S105

        self.user = UserFactory(email=self.valid_email)
        self.user.set_password(self.valid_password)
        self.user.save()

        self.client.post(reverse("auth:auth_request"), data={"email": self.valid_email})

        self.url = reverse("auth:login")

    def test_login_form_valid(self):
        form_data = {"password": self.valid_password}
        response = self.client.post(self.url, data=form_data)

        self.assertRedirects(response, reverse("cinema:home"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_login_form_invalid_password(self):
        form_data = {"password": self.invalid_password}
        response = self.client.post(self.url, data=form_data)

        form = response.context.get("form")
        self.assertTrue(form is not None)
        self.assertTrue(form.errors)
        self.assertIn("password", form.errors)
        self.assertIn("Password is not correct!", form.errors["password"])
        self.assertEqual(response.status_code, 200)

    def test_login_view_renders_correct_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "authentication/login_password.html")


class RegisterUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse("auth:register")
        self.valid_email = "newuser@example.com"
        self.client.post(reverse("auth:auth_request"), data={"email": self.valid_email})
        self.client.session["auth_email"] = self.valid_email
        self.client.session.save()

    def test_register_user_success(self):
        data = {
            "first_name": "Ali",
            "last_name": "Test",
            "password": "securepass123",
            "confirm_password": "securepass123",
        }
        response = self.client.post(self.register_url, data=data)

        self.assertRedirects(response, reverse("cinema:home"))
        self.assertTrue(User.objects.filter(email=self.valid_email).exists())
        user = User.objects.get(email=self.valid_email)
        self.assertTrue(user.check_password("securepass123"))
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_register_user_passwords_not_matching(self):
        data = {
            "first_name": "Ali",
            "last_name": "Test",
            "password": "securepass123",
            "confirm_password": "wrongpass456",
        }
        response = self.client.post(self.register_url, data=data)

        form = response.context["form"]
        self.assertTrue(form.errors)
        self.assertIn("confirm_password", form.errors)
        self.assertIn("Passwords do not match.", form.errors["confirm_password"])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email=self.valid_email).exists())

    def test_register_template_used(self):
        response = self.client.get(self.register_url)
        self.assertTemplateUsed(response, "authentication/register_user.html")


class LogoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="test@example.com", password="password123") # noqa: S106
        self.client.login(email="test@example.com", password="password123") # noqa: S106
        self.logout_url = reverse("auth:logout")
        self.auth_request_url = reverse("auth:auth_request")

    def test_logout_redirects_correctly(self):
        response = self.client.get(self.logout_url)

        self.assertRedirects(response, self.auth_request_url)
        self.assertNotIn("_auth_user_id", self.client.session)
