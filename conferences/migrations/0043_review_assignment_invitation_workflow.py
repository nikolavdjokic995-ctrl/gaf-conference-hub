from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0042_submission_author_countries_and_article_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="reviewassignment",
            name="invitation_status",
            field=models.CharField(
                choices=[
                    ("pending", "Invitation pending"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                ],
                default="pending",
                help_text="Reviewer invitation status before the review form is opened.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="reviewassignment",
            name="proposed_deadline",
            field=models.DateField(
                blank=True,
                help_text="Deadline proposed by the judge when inviting the reviewer.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="reviewassignment",
            name="accepted_deadline",
            field=models.DateField(
                blank=True,
                help_text="Final deadline accepted or requested by the reviewer.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="reviewassignment",
            name="deadline_extension_requested",
            field=models.BooleanField(
                default=False,
                help_text="Reviewer requested a different deadline when accepting the invitation.",
            ),
        ),
        migrations.AddField(
            model_name="reviewassignment",
            name="decline_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="reviewassignment",
            name="responded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
