from django.db import models
from django.utils import timezone
from django.db.models.functions import Lower
from django.contrib.auth import get_user_model
from django.conf import settings
import secrets

User = get_user_model() 

def _generate_share_token() -> str:
    # 32 bytes -> URL-safe token, very hard to guess
    return secrets.token_urlsafe(32)


class CustomerShareLink(models.Model):
    customer = models.ForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="share_links",
    )

    # Who created the link (audit + multi-broker safety)
    broker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_share_links",
    )

    token = models.CharField(max_length=128, unique=True, db_index=True, default=_generate_share_token)
    is_active = models.BooleanField(default=True, db_index=True)

    # Optional expiration
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self) -> bool:
        # Simple validity check (can be used in views)
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() >= self.expires_at:
            return False
        return True


class Customer(models.Model):
    ACTIVE_STATUS = [
        ("aktiv", "Aktiv"),
        ("ruhend", "Ruhend"),
    ]

    broker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="customers",
        blank=True,
        null=True
    )

    customer_number = models.CharField(
        max_length=11,  # "YYYY-XXXXXX" -> 4 + 1 + 6 = 11
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    active_status = models.CharField(
        max_length=50, choices=ACTIVE_STATUS, null=True, blank=True, default="aktiv"
    )
    appointment_at = models.DateTimeField(null=True, blank=True, db_index=True)
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
    notes = models.TextField(blank=True)

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
            cls.objects.filter(customer_number__startswith=str(year))
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
        indexes = [
            models.Index(fields=["customer_number"]),
            models.Index(fields=["last_name"]),
            models.Index(fields=["first_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["zip_code"]),
            models.Index(fields=["city"]),
            models.Index(fields=["street"]),
            models.Index(fields=["street", "zip_code"]),
            models.Index(fields=["broker", "last_name"]),
        ]

        constraints = [
            models.UniqueConstraint(
                Lower("first_name"),
                Lower("last_name"),
                Lower("zip_code"),
                Lower("street"),
                Lower("street"),
                "broker", 
                name="uniq_customer_identity_per_broker_ci", 
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
    policy_numbers = models.JSONField(default=list, blank=True)
    license_plates = models.JSONField(default=list, blank=True)

    contract_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="aktiv"
    )

    contract_typ = models.CharField(
        max_length=50,
        choices=CONTRACT_TYPES,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        policy = None
        if isinstance(self.policy_numbers, list) and self.policy_numbers:
            policy = self.policy_numbers[0]
        return f"Document {self.id} ({policy or 'no policy'}) {self.customer}"
