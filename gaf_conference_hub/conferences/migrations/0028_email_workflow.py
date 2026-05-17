from django.db import migrations, models
import django.db.models.deletion


DEFAULT_TEMPLATES = {
    "paper_submitted": {
        "subject": "Submission received — {{ paper_title }}",
        "body": "Dear {{ all_authors }},\n\nThis is to confirm that your paper:\n\n\"{{ paper_title }}\"\n\nhas been submitted to {{ conference_name }}.\n\nBest regards,\n{{ conference_name }}",
        "send_to_author": True,
        "send_to_coauthors": True,
    },
    "reviewer_assigned": {
        "subject": "Review assignment — {{ paper_title }}",
        "body": "Dear {{ reviewer_name }},\n\nYou have been assigned to review the paper:\n\n\"{{ paper_title }}\"\n\nReview link:\n{{ review_link }}\n\nBest regards,\n{{ conference_name }}",
        "send_to_author": False,
        "send_to_coauthors": False,
        "send_to_reviewer": True,
    },
    "revision_requested": {
        "subject": "Revision requested — {{ paper_title }}",
        "body": "Dear {{ all_authors }},\n\nA revision has been requested for your paper:\n\n\"{{ paper_title }}\"\n\nRevision instructions:\n{{ revision_message }}\n\nPlease upload the revised version here:\n{{ upload_revision_link }}\n\nBest regards,\n{{ conference_name }}",
        "send_to_author": True,
        "send_to_coauthors": True,
    },
    "revision_uploaded": {
        "subject": "Revision uploaded — {{ paper_title }}",
        "body": "A revised version has been uploaded for the paper:\n\n\"{{ paper_title }}\"\n\nSubmission result link:\n{{ submission_result_link }}",
        "send_to_author": False,
        "send_to_coauthors": False,
        "send_to_managers": True,
    },
    "accepted_for_layout": {
        "subject": "Paper ready for layout review — {{ paper_title }}",
        "body": "The paper:\n\n\"{{ paper_title }}\"\n\nhas been accepted for layout review.\n\nLayout decision link:\n{{ layout_decision_link }}",
        "send_to_author": False,
        "send_to_coauthors": False,
        "send_to_layout_reviewers": True,
        "send_to_managers": True,
    },
    "layout_revision_requested": {
        "subject": "Layout corrections requested — {{ paper_title }}",
        "body": "Dear {{ all_authors }},\n\nTechnical/layout corrections are required for your paper:\n\n\"{{ paper_title }}\"\n\nInstructions:\n{{ layout_revision_message }}\n\nPlease upload the corrected version here:\n{{ upload_revision_link }}\n\nBest regards,\n{{ conference_name }}",
        "send_to_author": True,
        "send_to_coauthors": True,
    },
    "layout_revision_uploaded": {
        "subject": "Layout corrected paper uploaded — {{ paper_title }}",
        "body": "A layout-corrected version has been uploaded for the paper:\n\n\"{{ paper_title }}\"\n\nLayout decision link:\n{{ layout_decision_link }}",
        "send_to_author": False,
        "send_to_coauthors": False,
        "send_to_layout_reviewers": True,
        "send_to_managers": True,
    },
    "final_accepted": {
        "subject": "Final acceptance — {{ paper_title }}",
        "body": "Dear {{ all_authors }},\n\nWe are pleased to inform you that your paper:\n\n\"{{ paper_title }}\"\n\nhas been finally accepted for {{ conference_name }}.\n\nBest regards,\n{{ conference_name }}",
        "send_to_author": True,
        "send_to_coauthors": True,
    },
    "rejected": {
        "subject": "Decision for your submission — {{ paper_title }}",
        "body": "Dear {{ all_authors }},\n\nWe regret to inform you that your paper:\n\n\"{{ paper_title }}\"\n\nhas not been accepted for {{ conference_name }}.\n\nDecision note:\n{{ final_comment }}\n\nBest regards,\n{{ conference_name }}",
        "send_to_author": True,
        "send_to_coauthors": True,
    },
}


def seed_email_templates(apps, schema_editor):
    Conference = apps.get_model("conferences", "Conference")
    EmailTemplate = apps.get_model("conferences", "EmailTemplate")

    for conference in Conference.objects.all():
        for event, data in DEFAULT_TEMPLATES.items():
            EmailTemplate.objects.update_or_create(
                conference=conference,
                event=event,
                defaults={
                    "enabled": True,
                    "subject": data["subject"],
                    "body": data["body"],
                    "send_to_author": data.get("send_to_author", True),
                    "send_to_coauthors": data.get("send_to_coauthors", True),
                    "send_to_reviewer": data.get("send_to_reviewer", False),
                    "send_to_managers": data.get("send_to_managers", False),
                    "send_to_layout_reviewers": data.get("send_to_layout_reviewers", False),
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0027_seed_default_sidebar_cards"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emailtemplate",
            name="event",
            field=models.CharField(max_length=80, choices=[
                ("paper_submitted", "Paper submission confirmation"),
                ("reviewer_assigned", "Reviewer assigned"),
                ("revision_requested", "Content revision requested"),
                ("revision_uploaded", "Content revision uploaded"),
                ("accepted_for_layout", "Accepted for layout review"),
                ("layout_revision_requested", "Layout corrections requested"),
                ("layout_revision_uploaded", "Layout corrected paper uploaded"),
                ("final_accepted", "Final acceptance"),
                ("rejected", "Rejected"),
            ]),
        ),
        migrations.AddField(
            model_name="emailtemplate",
            name="send_to_author",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="emailtemplate",
            name="send_to_coauthors",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="emailtemplate",
            name="send_to_reviewer",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="emailtemplate",
            name="send_to_managers",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="emailtemplate",
            name="send_to_layout_reviewers",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="EmailLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event", models.CharField(max_length=80)),
                ("recipient", models.EmailField(blank=True, max_length=254)),
                ("subject", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("sent", "Sent"), ("skipped", "Skipped"), ("failed", "Failed")], default="sent", max_length=20)),
                ("message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conference", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="conferences.conference")),
                ("submission", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="conferences.submission")),
                ("template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="conferences.emailtemplate")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.RunPython(seed_email_templates, migrations.RunPython.noop),
    ]
