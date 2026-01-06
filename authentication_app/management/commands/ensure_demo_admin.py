import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Ensure demo admin user exists and is in whitelist group (idempotent)."

    def handle(self, *args, **options):
        username = os.getenv("DEMO_ADMIN_USERNAME", "admin")
        email = os.getenv("DEMO_ADMIN_EMAIL", "admin@example.com")
        password = os.getenv("DEMO_ADMIN_PASSWORD", "")

        if not password:
            self.stdout.write(self.style.WARNING(
                "DEMO_ADMIN_PASSWORD is empty. Skipping demo admin creation."))
            return

        group, _ = Group.objects.get_or_create(name="whitelist")

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"Created demo superuser '{username}'."))

        if not user.groups.filter(name="whitelist").exists():
            user.groups.add(group)
            self.stdout.write(self.style.SUCCESS(
                f"Added '{username}' to 'whitelist' group."))

        self.stdout.write(self.style.SUCCESS("Demo admin ensured."))
