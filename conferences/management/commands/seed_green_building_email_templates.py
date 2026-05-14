from django.core.management.base import BaseCommand

from conferences.email_defaults import DEFAULT_EMAIL_TEMPLATES_2026
from conferences.models import Conference, EmailTemplate


class Command(BaseCommand):
    help = "Create or update the 15 Green Building 2026 automatic email template cards."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            dest="slug",
            default=None,
            help="Optional conference slug. If omitted, templates are created for all conferences.",
        )

    def handle(self, *args, **options):
        conferences = Conference.objects.all()
        if options["slug"]:
            conferences = conferences.filter(slug=options["slug"])

        total = 0
        for conference in conferences:
            for event, data in DEFAULT_EMAIL_TEMPLATES_2026.items():
                EmailTemplate.objects.update_or_create(
                    conference=conference,
                    event=event,
                    defaults={
                        "enabled": data.get("enabled", True),
                        "subject": data["subject"],
                        "body": data["body"],
                        "send_to_author": data.get("send_to_author", False),
                        "send_to_coauthors": data.get("send_to_coauthors", False),
                        "send_to_reviewer": data.get("send_to_reviewer", False),
                        "send_to_managers": data.get("send_to_managers", False),
                        "send_to_layout_reviewers": data.get("send_to_layout_reviewers", False),
                    },
                )
                total += 1
            self.stdout.write(self.style.SUCCESS(f"Seeded 15 templates for {conference.slug}"))

        if total == 0:
            self.stdout.write(self.style.WARNING("No conferences found."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. {total} template cards updated."))
