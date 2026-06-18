# Generated manually for GAF Conference Hub

from django.db import migrations


LEGACY_STATUS_TO_JUDGE_DECISION = {
    "accepted_for_layout": "accepted_for_layout",
    "layout_revision_required": "accepted_for_layout",
    "layout_revision_submitted": "accepted_for_layout",
    "final_accepted": "accepted_for_layout",
    "accepted": "accepted_for_layout",
    "rejected": "rejected",
}


def backfill_judge_decision(apps, schema_editor):
    Submission = apps.get_model("conferences", "Submission")

    for status, judge_decision in LEGACY_STATUS_TO_JUDGE_DECISION.items():
        Submission.objects.filter(
            judge_decision="",
            status=status,
        ).update(
            judge_decision=judge_decision,
        )


def reverse_backfill_judge_decision(apps, schema_editor):
    # Do not clear judge_decision values on reverse migration.
    # Some values may have been entered by judges after this migration ran.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0075_submission_judge_decision"),
    ]

    operations = [
        migrations.RunPython(
            backfill_judge_decision,
            reverse_backfill_judge_decision,
        ),
    ]
