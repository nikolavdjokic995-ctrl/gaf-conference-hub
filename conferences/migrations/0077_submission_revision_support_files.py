# Generated manually for GAF Conference Hub

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0076_backfill_submission_judge_decision"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="revision_response_file",
            field=models.FileField(
                blank=True,
                help_text="Author response to the reviewers.",
                max_length=500,
                null=True,
                upload_to="revision_response_files/",
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="revision_marked_file",
            field=models.FileField(
                blank=True,
                help_text="Marked-up revised manuscript showing all changes.",
                max_length=500,
                null=True,
                upload_to="revision_marked_papers/",
            ),
        ),
    ]
