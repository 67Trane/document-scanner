from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class CsrfViewTests(TestCase):
    def test_csrf_cookie_set(self):
        client = APIClient()
        response = client.get(reverse("csrf"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="alice",
            password="pass12345",
        )

    def test_login_logout_flow(self):
        response = self.client.post(
            reverse("login"),
            {"username": "alice", "password": "pass12345", "remember": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "alice")

        response = self.client.post(reverse("logout"), format="json")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, 403)

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            reverse("login"),
            {"username": "alice", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invalid credentials")