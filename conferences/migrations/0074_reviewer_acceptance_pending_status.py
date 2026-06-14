# Generated manually for GAF Conference Hub

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0073_submission_is_student_paper"),
    ]

    operations = [
        migrations.AlterField(
            model_name="submission",
            name="status",
            field=models.CharField(
                choices=[
                    ("submitted", "Submitted"),
                    ("reviewer_acceptance_pending", "Reviewer acceptance pending"),
                    ("under_review", "Under content review"),
                    ("reviews_completed", "Content review completed"),
                    ("reviewed_by_reviewer", "Reviewed by reviewer"),
                    ("revision_required", "Revision requested"),
                    ("paper_revision_completed", "Paper revision completed"),
                    ("accepted_for_layout", "Accepted for layout review"),
                    ("layout_revision_required", "Layout corrections requested"),
                    ("layout_revision_submitted", "Layout corrected paper submitted"),
                    ("final_accepted", "Final accepted"),
                    ("accepted", "Accepted (legacy)"),
                    ("rejected", "Rejected"),
                ],
                default="submitted",
                max_length=30,
            ),
        ),
    ]
