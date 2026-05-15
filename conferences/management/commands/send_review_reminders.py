from django.core.management.base import BaseCommand
from django.utils import timezone

from conferences.emails import send_event_email
from conferences.models import Review, ReviewAssignment


class Command(BaseCommand):
    help = "Send automatic reviewer reminders: due soon and overdue."

    def handle(self, *args, **options):
        today = timezone.now().date()
        sent_due_soon = 0
        sent_overdue = 0

        assignments = ReviewAssignment.objects.filter(
            role="content_reviewer",
            invitation_status="accepted",
        ).select_related("submission", "reviewer", "submission__conference")

        for assignment in assignments:
            submission = assignment.submission
            deadline = assignment.final_deadline()

            if not deadline:
                continue

            current_round = submission.revision_round or 0
            review_exists = Review.objects.filter(
                submission=submission,
                reviewer=assignment.reviewer,
                review_round=current_round,
            ).exists()

            if review_exists:
                continue

            days_until_due = (deadline - today).days

            if days_until_due == 2 and not assignment.due_soon_reminder_sent:
                send_event_email(
                    "review_due_soon",
                    submission,
                    reviewer=assignment.reviewer,
                    assignment=assignment,
                    extra={"days_until_due": "2"},
                )
                assignment.due_soon_reminder_sent = True
                assignment.save(update_fields=["due_soon_reminder_sent"])
                sent_due_soon += 1

            if days_until_due < 0 and not assignment.overdue_reminder_sent:
                send_event_email(
                    "review_overdue",
                    submission,
                    reviewer=assignment.reviewer,
                    assignment=assignment,
                    extra={"days_until_due": str(days_until_due)},
                )
                assignment.overdue_reminder_sent = True
                assignment.save(update_fields=["overdue_reminder_sent"])
                sent_overdue += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Review reminders sent. Due soon: {sent_due_soon}. Overdue: {sent_overdue}."
            )
        )
