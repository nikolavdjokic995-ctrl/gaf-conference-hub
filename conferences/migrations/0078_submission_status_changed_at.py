# Generated manually for tracking how long each submission has been in its current status.

from django.db import migrations, models
from django.db.models import F
from django.utils import timezone


def backfill_status_changed_at(apps, schema_editor):
    Submission = apps.get_model("conferences", "Submission")

    # Existing rows do not have a precise historical status-change timestamp.
    # updated_at is the best available approximation; created_at/timezone.now
    # are fallbacks for any unusual legacy rows.
    Submission.objects.filter(status_changed_at__isnull=True).update(
        status_changed_at=F("updated_at")
    )
    Submission.objects.filter(status_changed_at__isnull=True).update(
        status_changed_at=F("created_at")
    )
    Submission.objects.filter(status_changed_at__isnull=True).update(
        status_changed_at=timezone.now()
    )


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0077_submission_revision_support_files"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="status_changed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Date and time when the submission entered its current status.",
                null=True,
            ),
        ),
        migrations.RunPython(
            backfill_status_changed_at,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
