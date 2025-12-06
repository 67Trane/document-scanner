from django.db import models


class Customer(models.Model):
    SALUTATION_CHOICES = [
        ("Herr", "Herr"),
        ("Frau", "Frau"),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    street = models.CharField(max_length=200, null=True, blank=True)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, default="Germany")
    policy_number = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    license_plates = models.JSONField(default=list, blank=True)
    salutation = models.CharField(
        max_length=10,
        choices=SALUTATION_CHOICES,
        null=True,
        blank=True
    )

    def __str__(self):
        # For admin display
        return f"{self.last_name}, {self.first_name}"


class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("policy", "Versicherungsschein"),
        ("conditions", "Bedingungen"),
        ("cancellation", "Kündigung"),
        ("invoice", "Rechnung"),
        ("other", "Sonstiges"),
    ]

    SOURCE_CHOICES = [
        ("scanner", "Scanner"),
        ("upload", "Upload"),
        ("email", "Email"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    # Optional einfache Strings statt extra Tabellen:
    insurance_company_name = models.CharField(
        max_length=200, null=True, blank=True)
    insurance_type_name = models.CharField(
        max_length=100, null=True, blank=True)

    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
        default="other",
    )

    title = models.CharField(max_length=255)

    # WICHTIG: Du willst eh auf NAS speichern → String-Pfad reicht vollkommen
    file_path = models.CharField(max_length=500)

    original_filename = models.CharField(max_length=255, null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="scanner"
    )

    tags = models.CharField(max_length=255, null=True, blank=True)
    # Volltext aus PDF z.B. für Suche
    ocr_text = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title
