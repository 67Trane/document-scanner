from django.db import models

class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    street = models.CharField(max_length=200, null=True, blank=True)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, default="Germany")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # For admin display
        return f"{self.last_name}, {self.first_name}"


class InsuranceCompany(models.Model):
    name = models.CharField(max_length=200)
    street = models.CharField(max_length=200, null=True, blank=True)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=50, null=True, blank=True)
    website = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.name


class InsuranceType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Policy(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
        ("pending", "Pending"),
    ]

    PAYMENT_INTERVAL_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="policies")
    insurance_company = models.ForeignKey(InsuranceCompany, on_delete=models.PROTECT, related_name="policies")
    insurance_type = models.ForeignKey(InsuranceType, on_delete=models.PROTECT, related_name="policies")

    policy_number = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    premium_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_interval = models.CharField(
        max_length=20,
        choices=PAYMENT_INTERVAL_CHOICES,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # Example: "Allianz - Privathaftpflicht - 123456"
        return f"{self.insurance_company} - {self.insurance_type} - {self.policy_number}"


class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("policy", "Policy"),
        ("cancellation", "Cancellation"),
        ("invoice", "Invoice"),
        ("correspondence", "Correspondence"),
        ("other", "Other"),
    ]

    SOURCE_CHOICES = [
        ("scanner", "Scanner"),
        ("upload", "Upload"),
        ("email", "Email"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="documents")
    policy = models.ForeignKey(Policy, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")

    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES, default="other")
    title = models.CharField(max_length=255)

    # Later you can point this to a NAS path or FileField
    file = models.FileField(upload_to="documents/")  # or use a CharField for NAS path
    original_filename = models.CharField(max_length=255)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="scanner")

    tags = models.CharField(max_length=255, null=True, blank=True)  # e.g. "auto, haftpflicht"
    ocr_text = models.TextField(null=True, blank=True)  # fulltext from OCR

    def __str__(self):
        return self.title
