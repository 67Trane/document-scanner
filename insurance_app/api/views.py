from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from ..models import Customer
from .serializers import CustomerSerializer
from ..read_pdf import extract_pdf_text
from rest_framework import status, viewsets
from rest_framework.decorators import api_view


class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer



@api_view(["POST"])
def import_customer_from_pdf(request):
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

    serializer = CustomerSerializer(data=infos)
    serializer.is_valid(raise_exception=True)
    customer = serializer.save()

    return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)
