from rest_framework import serializers
from ..models import Customer, Document
from django.urls import reverse


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ["customer_number", "created_at", "updated_at"]


class DocumentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = "__all__"
        read_only_fields = ["id", "created_at", "customer"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        url = reverse("document_file", args=[obj.pk])
        return request.build_absolute_uri(url)
