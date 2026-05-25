from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import User, UserRole


class Phase2AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_customer(self):
        res = self.client.post(
            "/api/auth/register/",
            {
                "email": "cust@example.com",
                "password": "testpass12345",
                "first_name": "C",
                "last_name": "U",
                "role": "customer",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(email="cust@example.com").count(), 1)

    def test_login_returns_tokens(self):
        User.objects.create_user(
            email="u@example.com",
            password="pass12345678",
            role=UserRole.CUSTOMER,
        )
        res = self.client.post(
            "/api/auth/token/",
            {"email": "u@example.com", "password": "pass12345678"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_password_change_when_authenticated(self):
        u = User.objects.create_user(
            email="p@example.com",
            password="oldpass12345",
            role=UserRole.CUSTOMER,
        )
        self.client.force_authenticate(user=u)
        res = self.client.post(
            "/api/auth/password/change/",
            {"old_password": "oldpass12345", "new_password": "newpass12345"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        u.refresh_from_db()
        self.assertTrue(u.check_password("newpass12345"))
