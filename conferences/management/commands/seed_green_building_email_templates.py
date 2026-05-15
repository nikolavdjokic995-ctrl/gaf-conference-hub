from django.core.management.base import BaseCommand

from conferences.email_defaults import DEFAULT_EMAIL_TEMPLATES_2026
from conferences.models import Conference, EmailTemplate


class Command(BaseCommand):
    help = "Create missing Green Building 2026 automatic email template cards. Existing edited templates are not overwritten unless --overwrite is used."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            dest="slug",
            default=None,
            help="Optional conference slug. If omitted, templates are created for all conferences.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing templates with default text from conferences/email_defaults.py.",
        )

    def handle(self, *args, **options):
        queryset = Conference.objects.all().order_by("slug")
        slug = options.get("slug")
        overwrite = options.get("overwrite")

        if slug:
            queryset = queryset.filter(slug=slug)

        conferences = list(queryset)

        if not conferences:
            self.stdout.write(self.style.WARNING("No conferences found for this slug."))
            existing = list(Conference.objects.values_list("slug", "title_en"))
            if existing:
                self.stdout.write("Available conferences:")
                for item_slug, title in existing:
                    self.stdout.write(f"- {item_slug}: {title}")
            else:
                self.stdout.write("Your local database has no conferences. This can be normal locally; run this command on Render where the conference exists.")
            return

        total_created = 0
        total_updated = 0
        total_existing = 0

        for conference in conferences:
            self.stdout.write(f"Seeding email templates for: {conference.slug}")

            for event, data in DEFAULT_EMAIL_TEMPLATES_2026.items():
                defaults = {
                    "enabled": data.get("enabled", True),
                    "subject": data["subject"],
                    "body": data["body"],
                    "send_to_author": data.get("send_to_author", False),
                    "send_to_coauthors": data.get("send_to_coauthors", False),
                    "send_to_reviewer": data.get("send_to_reviewer", False),
                    "send_to_managers": data.get("send_to_managers", False),
                    "send_to_layout_reviewers": data.get("send_to_layout_reviewers", False),
                }

                template = EmailTemplate.objects.filter(conference=conference, event=event).first()

                if template is None:
                    EmailTemplate.objects.create(
                        conference=conference,
                        event=event,
                        **defaults,
                    )
                    total_created += 1
                    self.stdout.write(self.style.SUCCESS(f"  + created: {event}"))
                elif overwrite:
                    for field, value in defaults.items():
                        setattr(template, field, value)
                    template.save()
                    total_updated += 1
                    self.stdout.write(self.style.WARNING(f"  ~ overwritten: {event}"))
                else:
                    total_existing += 1
                    self.stdout.write(f"  = kept existing: {event}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {total_created}, overwritten: {total_updated}, kept existing: {total_existing}."
        ))
