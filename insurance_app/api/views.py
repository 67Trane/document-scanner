from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse, Http404
import os
from ..models import Customer, Document
from .serializers import CustomerSerializer, DocumentSerializer
from ..read_pdf import extract_pdf_text


class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Document.objects.select_related("customer").all()
    serializer_class = DocumentSerializer


class DocumentImportView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        pdf_path = request.data.get("pdf_path")

        if not pdf_path:
            return Response(
                {"error": "pdf_path fehlt"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            infos = extract_pdf_text(pdf_path)
        except FileNotFoundError:
            return Response(
                {"error": f"Datei nicht gefunden: {pdf_path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Fehler beim Lesen der PDF: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ---- Customer-Daten aus dem PDF ----
        customer_data = {
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
        }

        # ---- Versuche, existierenden Customer zu finden ----
        lookup = {
            "first_name": customer_data["first_name"],
            "last_name": customer_data["last_name"],
            "zip_code": customer_data["zip_code"],
            "street": customer_data["street"],
        }

        # Filter nur wenn wenigstens Name + Straße + PLZ da sind
        qs = Customer.objects.all()
        for field, value in lookup.items():
            if value:
                qs = qs.filter(**{field: value})

        customer = qs.first()
        created = False

        if not customer:
            # Neuen Customer anlegen
            serializer = CustomerSerializer(data=customer_data)
            serializer.is_valid(raise_exception=True)
            customer = serializer.save()
            created = True

        # ---- Document anlegen ----
        raw_text = infos.get("raw_text", "")
        policy_number = infos.get("policy_number")
        license_plates = infos.get("license_plates") or []
        contract_typ = infos.get("contract_typ")
        contract_status = infos.get("contract_status")

        document = Document.objects.create(
            customer=customer,
            file_path=pdf_path,
            raw_text=raw_text,
            policy_number=policy_number,
            license_plates=license_plates,
            contract_typ=contract_typ,
            contract_status="aktiv"
        )

        doc_serializer = DocumentSerializer(
            document, context={"request": request})

        return Response(
            {
                "customer_created": created,
                "customer": CustomerSerializer(customer).data,
                "document": doc_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentFileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk, *args, **kwargs):
        try:
            doc = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            raise Http404("Document not found")

        if not doc.file_path or not os.path.exists(doc.file_path):
            raise Http404("File not found")

        return FileResponse(
            open(doc.file_path, "rb"),
            content_type="application/pdf",
        )
