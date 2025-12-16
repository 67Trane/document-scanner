from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse, Http404
from django.db.models import Q
from django.core.exceptions import ValidationError
import os
from django.db import transaction, IntegrityError

from ..models import Customer, Document
from .serializers import CustomerSerializer, DocumentSerializer
from ..read_pdf import extract_pdf_text
from ..services import move_pdf_to_customer_folder


class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CustomerSerializer

    def get_queryset(self):
        qs = Customer.objects.all()

        q = self.request.query_params.get("q")
        if q:
            q = q.strip()
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
                | Q(zip_code__icontains=q)
                | Q(city__icontains=q)
                | Q(customer_number__icontains=q)
            )

        return qs


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Document.objects.select_related("customer").all()
    serializer_class = DocumentSerializer

    def get_queryset(self):
        qs = Document.objects.select_related("customer").all()

        customer_id = self.request.query_params.get("customer")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        return qs


class DocumentImportView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        pdf_path = request.data.get("pdf_path")

        if not pdf_path:
            return Response(
                {"error": "pdf_path fehlt"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ---- PDF auslesen ----
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
            "active_status": infos.get("active_status")
        }

        # ---- Customer finden oder anlegen ----
        first_name = (customer_data.get("first_name") or "").strip()
        last_name = (customer_data.get("last_name") or "").strip()
        zip_code = (customer_data.get("zip_code") or "").strip()
        street = (customer_data.get("street") or "").strip()

        created = False
        customer = None

        # 1) OCR-robuster Kandidaten-Check (Adresse)
        address_candidates = Customer.objects.filter(
            street__iexact=street,
            zip_code=zip_code,
        )

        if address_candidates.count() == 1:
            # genau 1 Person an der Adresse -> nimm die, egal ob OCR den Vornamen verhunzt
            customer = address_candidates.first()
        elif address_candidates.count() > 1:
            # mehrere Personen an der Adresse -> nicht automatisch raten
            return Response(
                {
                    "error": "Mehrere Kunden an dieser Adresse gefunden. Bitte manuell auswählen.",
                    "candidates": [
                        {
                            "id": c.id,
                            "first_name": c.first_name,
                            "last_name": c.last_name,
                            "customer_number": c.customer_number,
                        }
                        for c in address_candidates
                    ],
                },
                status=status.HTTP_409_CONFLICT,
            )

        # 2) Wenn kein eindeutiger Kandidat: exact lookup (dein bisheriger Weg)
        if not customer:
            lookup = {
                "first_name": first_name,
                "last_name": last_name,
                "zip_code": zip_code,
                "street": street,
            }
            lookup = {k: v for k, v in lookup.items() if v}

            customer = Customer.objects.filter(**lookup).first()

        # 3) Wenn immer noch keiner: anlegen (atomic + IntegrityError)
        if not customer:
            try:
                with transaction.atomic():
                    serializer = CustomerSerializer(data=customer_data)
                    serializer.is_valid(raise_exception=True)
                    customer = serializer.save()
                    created = True
            except IntegrityError:
                customer = Customer.objects.get(**lookup)
                created = False


        # ---- PDF in Kundenordner verschieben (IMMER nach customer!) ----
        try:
            new_file_path = move_pdf_to_customer_folder(pdf_path, customer)
        except FileNotFoundError:
            return Response(
                {"error": f"Datei nicht gefunden (beim Verschieben): {pdf_path}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (ValueError, ValidationError) as e:
            return Response(
                {"error": f"Fehler beim Verschieben der Datei: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Unerwarteter Fehler beim Verschieben der Datei: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


        # ---- Document anlegen ----
        raw_text = infos.get("raw_text", "")
        policy_number = infos.get("policy_number")
        license_plates = infos.get("license_plates") or []
        contract_typ = infos.get("contract_typ")
        contract_status = infos.get("contract_status") or "aktiv"

        document = Document.objects.create(
            customer=customer,
            file_path=new_file_path,
            raw_text=raw_text,
            policy_number=policy_number,
            license_plates=license_plates,
            contract_typ=contract_typ,
            contract_status=contract_status,
        )

        doc_serializer = DocumentSerializer(
            document, context={"request": request}
        )

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
