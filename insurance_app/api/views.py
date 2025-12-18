from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import FileResponse, Http404
from django.db.models import Q
from django.core.exceptions import ValidationError
import os

from ..models import Customer, Document
from .serializers import CustomerSerializer, DocumentSerializer
from ..services.extract_pdf_text import extract_pdf_text
from ..services.move_pdf import move_pdf_to_customer_folder
from ..services.customer_matching import (
    find_or_create_customer,
    AmbiguousCustomerError,
)



class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Customer.objects.all()

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


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = DocumentSerializer
    queryset = Document.objects.select_related("customer")

    def get_queryset(self):
        queryset = super().get_queryset()

        # Optional filter by customer id
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        return queryset


class DocumentImportView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        pdf_path = request.data.get("pdf_path")

        if not pdf_path:
            return Response(
                {"error": "pdf_path is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1) Extract data from PDF
        try:
            infos = extract_pdf_text(pdf_path)
        except FileNotFoundError:
            return Response(
                {"error": f"File not found: {pdf_path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to read PDF: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 2) Build customer payload from OCR data
        customer_data = self._build_customer_data(infos)

        # 3) Find or create customer (OCR-safe logic lives in service)
        try:
            customer, created = find_or_create_customer(customer_data)
        except AmbiguousCustomerError as e:
            candidates_list = []

            for customer in e.candidates:
                candidates_list.append({
                    "id": customer.id,
                    "first_name": customer.first_name,
                    "last_name": customer.last_name,
                    "customer_number": customer.customer_number,
                })

            return Response(
                {
                    "error": "Multiple customers found at this address.",
                    "candidates": candidates_list,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # 4) Move PDF into customer folder
        try:
            new_file_path = move_pdf_to_customer_folder(pdf_path, customer)
        except FileNotFoundError:
            return Response(
                {"error": f"File not found while moving: {pdf_path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (ValueError, ValidationError) as e:
            return Response(
                {"error": f"Invalid file operation: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Unexpected file error: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 5) Create document entry
        document = Document.objects.create(
            customer=customer,
            file_path=new_file_path,
            raw_text=infos.get("raw_text", ""),
            policy_number=infos.get("policy_number"),
            license_plates=infos.get("license_plates") or [],
            contract_typ=infos.get("contract_typ"),
            contract_status=infos.get("contract_status") or "aktiv",
        )

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

    def _build_customer_data(self, infos: dict) -> dict:
        """
        Build a clean customer payload from OCR data.
        Keep normalization minimal – matching logic lives elsewhere.
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
            "active_status": infos.get("active_status"),
        }


class DocumentFileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
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
