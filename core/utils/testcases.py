from rest_framework.test import APIClient, APITestCase


class AppAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
