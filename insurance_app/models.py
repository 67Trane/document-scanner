
from django.db import models
from django.utils import timezone
from django.db.models.functions import Lower

class Customer(models.Model):
    ACTIVE_STATUS = [
        ("aktiv", "Aktiv"),
        ("ruhend", "Ruhend"),
    ]

    customer_number = models.CharField(
        max_length=11,  # "YYYY-XXXXXX" -> 4 + 1 + 6 = 11
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )

    active_status = models.CharField(
        max_length=50,
        choices=ACTIVE_STATUS,
        null=True,
        blank=True,
    )
    salutation = models.CharField(max_length=10, blank=True)
    first_name = models.CharField(max_length=100, blank=True, db_index=True)
    last_name = models.CharField(max_length=100, blank=True, db_index=True)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True, null=True, db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    street = models.CharField(max_length=255, blank=True)
    zip_code = models.CharField(max_length=10, blank=True, db_index=True)
    city = models.CharField(max_length=100, blank=True,
                            null=True, db_index=True)
    country = models.CharField(max_length=100, default="Germany")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer_number or '-'} - {self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if not self.customer_number:
            self.customer_number = self._generate_customer_number()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_customer_number(cls) -> str:
        """
        Erzeugt eine Kundennummer im Format YYYY-XXXXXX.
        Beispiel: 2025-000001
        """
        year = timezone.now().year

        # Alle Kunden aus diesem Jahr holen
        last_customer = (
            cls.objects
            .filter(customer_number__startswith=str(year))
            .order_by("-customer_number")
            .first()
        )

        if last_customer and last_customer.customer_number:
            # Kundennummer-Teil nach dem '-' holen und in int umwandeln
            _, last_seq_str = last_customer.customer_number.split("-")
            last_seq = int(last_seq_str)
            next_seq = last_seq + 1
        else:
            next_seq = 1

        return f"{year}-{next_seq:06d}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("first_name"),
                Lower("last_name"),
                Lower("zip_code"),
                Lower("street"),
                name="uniq_customer_identity_ci",
            )
        ]


class Document(models.Model):

    STATUS_CHOICES = [
        ("aktiv", "Aktiv"),
        ("ruhend", "Ruhend"),
    ]

    CONTRACT_TYPES = [
        ("kfz", "Kfz-Versicherung"),
        ("haftpflicht", "Privat-Haftpflicht"),
        ("hausrat", "Hausrat"),
        ("rechtschutz", "Rechtsschutz"),
        ("wohngebaeude", "Wohngebäudeversicherung"),
        ("unfall", "Unfallversicherung"),
        ("lebensversicherung", "Lebensversicherung"),
        ("berufsunfaehigkeit", "Berufsunfähigkeitsversicherung"),
        ("krankenversicherung", "Private Krankenversicherung"),
        ("tierversicherung", "Tierhalterhaftpflicht / Tierkranken"),
        ("reise", "Reiseversicherung"),
    ]

    customer = models.ForeignKey(
        Customer,
        related_name="documents",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    file_path = models.CharField(max_length=512)
    raw_text = models.TextField(blank=True, null=True)
    policy_number = models.CharField(max_length=100, null=True, blank=True)
    license_plates = models.JSONField(default=list, blank=True)

    contract_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="aktiv"
    )

    contract_typ = models.CharField(
        max_length=50,
        choices=CONTRACT_TYPES,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document {self.id} ({self.policy_number or 'no policy'})"
