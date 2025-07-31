from django.test import TestCase
from django.urls import reverse

class PaymentLinkViewTests(TestCase):
    def test_create_payment_link_view_exists(self):
        url = reverse('payments:create_payment_link')
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])  # 200 OK or 302 Redirect

    def test_api_create_payment_link_exists(self):
        url = reverse('payments:api_create_payment_link')
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 405, 302])  # 405 if POST required, etc.