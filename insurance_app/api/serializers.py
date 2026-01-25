from rest_framework import serializers
from ..models import Customer, Document, CustomerShareLink
from django.urls import reverse
from django.conf import settings


class CustomerShareLinkSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = CustomerShareLink
        fields = ["id", "token", "url",
                  "is_active", "expires_at", "created_at"]
        read_only_fields = ["id", "token", "url", "created_at"]

    def get_url(self, obj):
        # NOTE: Put FRONTEND_URL in settings (e.g. http://localhost:4200)
        base = getattr(settings, "FRONTEND_URL", "").rstrip("/")
        return f"{base}/#/share/{obj.token}" if base else obj.token


class PublicDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "created_at", "contract_typ",
                  "contract_status", "policy_numbers", "license_plates"]


class PublicCustomerSerializer(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ["id", "first_name", "last_name", "street",
                  "zip_code", "city", "country", "documents"]

    def get_documents(self, obj):
        docs = Document.objects.filter(customer=obj).order_by("-id")
        return PublicDocumentSerializer(docs, many=True).data


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ["customer_number",
                            "created_at", "updated_at", "broker"]

    def validate(self, attrs):
        # IMPORTANT: normalize identity fields so uniqueness works reliably
        for f in ["first_name", "last_name", "street", "zip_code"]:
            if f in attrs and isinstance(attrs[f], str):
                attrs[f] = attrs[f].strip()

        # choose ONE consistent rule (example: title case for names)
        if "first_name" in attrs and attrs["first_name"]:
            attrs["first_name"] = attrs["first_name"].title()
        if "last_name" in attrs and attrs["last_name"]:
            attrs["last_name"] = attrs["last_name"].title()

        return attrs


class DocumentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    contract_typ_display = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = "__all__"
        read_only_fields = ["id", "created_at", "customer"]

    def get_file_url(self, obj):
        # IMPORTANT: return RELATIVE URL
        return reverse("document_file", kwargs={"pk": obj.pk})

    def get_contract_typ_display(self, obj):
        # IMPORTANT: Django provides get_<field>_display() for choices
        return obj.get_contract_typ_display() if obj.contract_typ else None
