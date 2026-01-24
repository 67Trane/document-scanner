import logging
import os

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication_app.api.permissions import HasImportToken, IsInWhitelistGroup

from ..models import Customer, Document
from .serializers import CustomerSerializer, DocumentSerializer
from ..services.extract_pdf_text import extract_pdf_text
from ..services.move_pdf import move_pdf_to_customer_folder, move_pdf_to_unassigned_folder
from ..services.customer_matching import (
    find_or_create_customer,
    AmbiguousCustomerError,
    UnresolvedCustomerError,
)

from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsInWhitelistGroup]

    def get_queryset(self):
        """Return customers filtered by optional search tokens."""
        qs = Customer.objects.filter(broker=self.request.user)

        q = (self.request.query_params.get("q") or "").strip()
        if q:
            tokens = [t for t in q.split() if t]
            for t in tokens:
                qs = qs.filter(
                    Q(first_name__icontains=t)
                    | Q(last_name__icontains=t)
                    | Q(email__icontains=t)
                    | Q(zip_code__icontains=t)
                    | Q(city__icontains=t)
                    | Q(customer_number__icontains=t)
                )

        return qs.order_by("id")

    def perform_create(self, serializer):
        serializer.save(broker=self.request.user)

class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsInWhitelistGroup]
    serializer_class = DocumentSerializer
    queryset = Document.objects.select_related("customer").order_by("-id")

    def get_queryset(self):
        """Return documents with an optional customer filter."""
        queryset = Document.objects.select_related("customer").filter(
            customer__broker=self.request.user
        ).order_by("-id")

        # Optional filter by customer id
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        return queryset


class DocumentImportView(APIView):
    authentication_classes = []
    permission_classes = [HasImportToken]

    def post(self, request):
        """Import a PDF from disk and create customer/document records."""
        broker_id = request.headers.get("X-Broker-Id")
        broker = User.objects.get(id=int(broker_id))
        
        pdf_path = request.data.get("pdf_path")

        if not isinstance(pdf_path, str) or not pdf_path.strip():
            return Response(
                {"error": "pdf_path is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pdf_path = pdf_path.strip()

        # 1) Extract data from PDF
        infos, error_response = self._extract_infos(pdf_path)
        if error_response:
            return error_response

        # 2) Build customer payload from OCR data
        customer_data = self._build_customer_data(infos)

        # 3) Find or create customer (OCR-safe logic lives in service)
        customer, created, error_response = self._resolve_customer(customer_data, broker)
        if error_response:
            return error_response

        # 4) Move PDF into customer folder
        new_file_path, error_response = self._move_pdf(pdf_path, customer)
        if error_response:
            return error_response

        # 5) Create document entry
        document = self._create_document(customer, new_file_path, infos)

        return Response(
            {
                "customer_created": created,
                "customer": CustomerSerializer(customer).data,
                "document": DocumentSerializer(
                    document, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def _extract_infos(self, pdf_path):
        try:
            return extract_pdf_text(pdf_path), None
        except FileNotFoundError:
            return None, Response(
                {"error": f"File not found: {pdf_path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Failed to read PDF", extra={"pdf_path": pdf_path})
            return None, Response(
                {"error": "Failed to read PDF."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _resolve_customer(self, customer_data, broker):
        try:
            customer, created = find_or_create_customer(customer_data, broker=broker)
            return customer, created, None
        except UnresolvedCustomerError:
            return None, False, None
        except AmbiguousCustomerError as e:
            candidates_list = [
                {
                    "id": customer.id,
                    "first_name": customer.first_name,
                    "last_name": customer.last_name,
                    "customer_number": customer.customer_number,
                }
                for customer in e.candidates
            ]
            return (
                None,
                None,
                Response(
                    {
                        "error": "Multiple customers found at this address.",
                        "candidates": candidates_list,
                    },
                    status=status.HTTP_409_CONFLICT,
                ),
            )

    def _move_pdf(self, pdf_path, customer):
        try:
            if customer is None:
                return move_pdf_to_unassigned_folder(pdf_path), None
            return move_pdf_to_customer_folder(pdf_path, customer), None
        except FileNotFoundError:
            return None, Response(
                {"error": f"File not found while moving: {pdf_path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (ValueError, ValidationError) as e:
            return None, Response(
                {"error": f"Invalid file operation: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception(
                "Unexpected file error while moving PDF",
                extra={"pdf_path": pdf_path, "customer_id": getattr(customer, "id", None)},
            )
            return None, Response(
                {"error": "Unexpected file error while moving PDF."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _create_document(self, customer, new_file_path, infos):
        return Document.objects.create(
            customer=customer,
            file_path=new_file_path,
            raw_text=infos.get("raw_text", ""),
            policy_numbers=infos.get("policy_numbers"),
            license_plates=infos.get("license_plates") or [],
            contract_typ=infos.get("contract_typ"),
            contract_status=infos.get("contract_status") or "aktiv",
        )

    def _build_customer_data(self, infos: dict) -> dict:
        """
        Build a clean customer payload from OCR data.
        Keep normalization minimal; matching logic lives elsewhere.
        """
        return {
            "salutation": infos.get("salutation") or "",
            "first_name": infos.get("first_name") or "",
            "last_name": infos.get("last_name") or "",
            "street": infos.get("street") or "",
            "zip_code": infos.get("zip_code") or "",
            "city": infos.get("city") or "",
            "country": infos.get("country") or "Germany",
            "email": infos.get("email") or "",
            "phone": infos.get("phone") or "",
            "date_of_birth": infos.get("date_of_birth"),
            "active_status": infos.get("active_status") or "aktiv",
        }


class DocumentFileView(APIView):
    permission_classes = [IsAuthenticated, IsInWhitelistGroup]

    def get(self, request, pk):
        """Return the stored PDF file for a document."""
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404("Document not found")

        if not document.file_path or not os.path.exists(document.file_path):
            raise Http404("File not found")

        return FileResponse(
            open(document.file_path, "rb"),
            content_type="application/pdf",
        )