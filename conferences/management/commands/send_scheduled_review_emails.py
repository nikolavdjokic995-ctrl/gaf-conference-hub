from django.core.management.base import BaseCommand

from conferences.email_automation import process_scheduled_review_emails


class Command(BaseCommand):
    help = "Send due-soon and overdue review reminder emails. Safe to run repeatedly."

    def handle(self, *args, **options):
        result = process_scheduled_review_emails()
        self.stdout.write(self.style.SUCCESS(
            f"Done. Due soon sent: {result['due_soon_sent']}; overdue sent: {result['overdue_sent']}; skipped: {result['skipped']}."
        ))
