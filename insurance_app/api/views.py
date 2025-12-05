from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from ..models import Customer
from .serializers import CustomerSerializer
from ..read_pdf import extract_pdf_text

class Customers(ListAPIView):
    permission_classes = [AllowAny]
    queryset = Customer.objects.all()

    serializer_class = CustomerSerializer

class Test(APIView):
    permission_classes = [AllowAny]
    def get(request, self):
        pdf_path = "C:/Users/67Trane/epson-test/test_run.pdf"
        test = extract_pdf_text(pdf_path)
        return Response(test)