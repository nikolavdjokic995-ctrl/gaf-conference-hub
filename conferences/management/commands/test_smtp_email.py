from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a simple SMTP test email without using workflow templates."

    def add_arguments(self, parser):
        parser.add_argument("to", help="Recipient email address for the SMTP test.")

    def handle(self, *args, **options):
        recipient = options["to"]
        subject = "[TEST] Green Building Conference SMTP check"
        body = (
            "This is a simple SMTP test from the Green Building Conference platform.\n\n"
            f"EMAIL_HOST={getattr(settings, 'EMAIL_HOST', '')}\n"
            f"EMAIL_PORT={getattr(settings, 'EMAIL_PORT', '')}\n"
            f"EMAIL_USE_TLS={getattr(settings, 'EMAIL_USE_TLS', '')}\n"
            f"DEFAULT_FROM_EMAIL={getattr(settings, 'DEFAULT_FROM_EMAIL', '')}\n"
        )
        try:
            sent = send_mail(
                subject,
                body,
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [recipient],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f"SMTP test failed: {exc}")

        if sent:
            self.stdout.write(self.style.SUCCESS(f"SMTP test email sent to {recipient}."))
        else:
            raise CommandError("SMTP test did not send any message, but no exception was raised.")
