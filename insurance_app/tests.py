from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from insurance_app.models import Customer, Document
from insurance_app.services.customer_matching import AmbiguousCustomerError


class DocumentModelTests(TestCase):
    def test_document_str_uses_policy_numbers(self):
        document = Document.objects.create(
            file_path="test.pdf",
            policy_numbers=["K 123-456789/1"],
        )

        self.assertIn("K 123-456789/1", str(document))

    def test_document_str_fallback(self):
        document = Document.objects.create(
            file_path="test.pdf",
            policy_numbers=[],
        )

        self.assertIn("no policy", str(document))


class DocumentImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            zip_code="12345",
            street="Main St",
        )

    @override_settings(DOCUMENT_IMPORT_TOKEN="token")
    @patch("insurance_app.api.views.move_pdf_to_customer_folder")
    @patch("insurance_app.api.views.find_or_create_customer")
    @patch("insurance_app.api.views.extract_pdf_text")
    def test_import_document_success(
        self,
        mock_extract_pdf_text,
        mock_find_or_create_customer,
        mock_move_pdf,
    ):
        mock_extract_pdf_text.return_value = {
            "raw_text": "raw",
            "policy_numbers": ["K 123-456789/1"],
            "license_plates": ["B-AB 123"],
            "contract_typ": "kfz",
            "contract_status": "aktiv",
        }
        mock_find_or_create_customer.return_value = (self.customer, True)
        mock_move_pdf.return_value = "C:\\docs\\file.pdf"

        response = self.client.post(
            reverse("import_document_from_pdf"),
            {"pdf_path": "C:\\incoming\\file.pdf"},
            format="json",
            HTTP_X_IMPORT_TOKEN="token",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["customer_created"])
        self.assertEqual(payload["customer"]["id"], self.customer.id)
        self.assertEqual(payload["document"]["file_path"], "C:\\docs\\file.pdf")

    @override_settings(DOCUMENT_IMPORT_TOKEN="token")
    def test_import_document_requires_pdf_path(self):
        response = self.client.post(
            reverse("import_document_from_pdf"),
            {},
            format="json",
            HTTP_X_IMPORT_TOKEN="token",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "pdf_path is required")

    @override_settings(DOCUMENT_IMPORT_TOKEN="token")
    @patch("insurance_app.api.views.find_or_create_customer")
    @patch("insurance_app.api.views.extract_pdf_text")
    def test_import_document_ambiguous_customer(
        self,
        mock_extract_pdf_text,
        mock_find_or_create_customer,
    ):
        customer_two = Customer.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            zip_code="12345",
            street="Main St",
        )
        mock_extract_pdf_text.return_value = {"raw_text": "raw"}
        mock_find_or_create_customer.side_effect = AmbiguousCustomerError(
            [self.customer, customer_two]
        )

        response = self.client.post(
            reverse("import_document_from_pdf"),
            {"pdf_path": "C:\\incoming\\file.pdf"},
            format="json",
            HTTP_X_IMPORT_TOKEN="token",
        )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["error"], "Multiple customers found at this address.")
        self.assertEqual(len(payload["candidates"]), 2)