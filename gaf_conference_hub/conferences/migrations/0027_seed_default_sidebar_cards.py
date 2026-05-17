from django.db import migrations


def seed_default_sidebar_cards(apps, schema_editor):
    Conference = apps.get_model("conferences", "Conference")
    ConferenceSidebarCard = apps.get_model("conferences", "ConferenceSidebarCard")

    for conference in Conference.objects.all():
        if ConferenceSidebarCard.objects.filter(conference=conference).exists():
            continue

        ConferenceSidebarCard.objects.create(
            conference=conference,
            eyebrow="Submission guide",
            title="How to submit",
            description=(
                "1. Review the topics\n"
                "Choose the conference topic that best matches your paper.\n\n"
                "2. Read the documents\n"
                "Use the available guidelines and templates before submitting.\n\n"
                "3. Follow the workflow\n"
                "Track your paper status from submission to final decision."
            ),
            order=1,
            enabled=True,
        )

        date_lines = []
        if getattr(conference, "submission_deadline", None):
            date_lines.append(f"Submission deadline\n{conference.submission_deadline}")
        if getattr(conference, "review_deadline", None):
            date_lines.append(f"Review deadline\n{conference.review_deadline}")

        conference_dates = str(conference.start_date)
        if getattr(conference, "end_date", None):
            conference_dates += f" – {conference.end_date}"
        date_lines.append(f"Conference dates\n{conference_dates}")

        ConferenceSidebarCard.objects.create(
            conference=conference,
            eyebrow="Timeline",
            title="Important dates",
            description="\n\n".join(date_lines),
            order=2,
            enabled=True,
        )

        useful_lines = []
        if getattr(conference, "registration_url", None):
            useful_lines.append(f"Registration\n{conference.registration_url}")
        if getattr(conference, "contact_email", None):
            useful_lines.append(f"Contact\n{conference.contact_email}")

        if useful_lines:
            ConferenceSidebarCard.objects.create(
                conference=conference,
                eyebrow="Links",
                title="Useful information",
                description="\n\n".join(useful_lines),
                order=3,
                enabled=True,
            )


def unseed_default_sidebar_cards(apps, schema_editor):
    ConferenceSidebarCard = apps.get_model("conferences", "ConferenceSidebarCard")
    ConferenceSidebarCard.objects.filter(
        title__in=["How to submit", "Important dates", "Useful information"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0026_alter_review_auto_score_recalculate"),
    ]

    operations = [
        migrations.RunPython(seed_default_sidebar_cards, unseed_default_sidebar_cards),
    ]
