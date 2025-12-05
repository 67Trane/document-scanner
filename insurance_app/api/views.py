from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from ..models import Customer
from .serializers import CustomerSerializer
from ..read_pdf import extract_pdf_text


class Customers(APIView):
    permission_classes = [AllowAny]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def post(self, request):
        pdf_path = "C:/Users/67Trane/epson-test/test_run.pdf"
        infos = extract_pdf_text(pdf_path)
        customer = Customer.objects.create(**infos)
        serializer = CustomerSerializer(customer)
        return Response(serializer.data, status=201)


# class Test(APIView):
#     permission_classes = [AllowAny]

#     def get(self, request):
#         pdf_path = "C:/Users/67Trane/epson-test/test_run.pdf"
#         infos = extract_pdf_text(pdf_path)
#         return Response(infos)
