from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class Test(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"message": "API funktioniert!"})
