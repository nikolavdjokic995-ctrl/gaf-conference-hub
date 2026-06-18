from django.core.management.base import BaseCommand

from conferences.email_automation import process_scheduled_review_emails


class Command(BaseCommand):
    help = "Send automatic reviewer reminders: due soon and overdue."

    def handle(self, *args, **options):
        result = process_scheduled_review_emails()
        self.stdout.write(
            self.style.SUCCESS(
                "Review reminders sent. "
                f"Due soon: {result['due_soon_sent']}. "
                f"Overdue: {result['overdue_sent']}. "
                f"Skipped: {result['skipped']}."
            )
        )
