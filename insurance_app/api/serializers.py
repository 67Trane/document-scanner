from rest_framework import serializers
from ..models import Customer, Document
from django.urls import reverse


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ["customer_number", "created_at", "updated_at"]

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
