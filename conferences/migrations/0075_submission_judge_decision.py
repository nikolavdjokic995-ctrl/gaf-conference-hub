# Generated manually for GAF Conference Hub

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0074_reviewer_acceptance_pending_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="judge_decision",
            field=models.CharField(
                blank=True,
                choices=[
                    ("accepted_for_layout", "Accept in present form"),
                    ("minor_revision", "Accept after minor revision"),
                    ("revision_required", "Reconsider after major revision"),
                    ("rejected", "Reject"),
                ],
                help_text="Latest judge decision selected on the Judge decision form.",
                max_length=30,
            ),
        ),
    ]
