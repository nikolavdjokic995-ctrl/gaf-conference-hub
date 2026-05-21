from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0068_remove_conference_hub_background_color_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="submission",
            name="status",
            field=models.CharField(
                choices=[
                    ("submitted", "Submitted"),
                    ("under_review", "Under content review"),
                    ("reviews_completed", "Content review completed"),
                    ("reviewed_by_reviewer", "Reviewed by reviewer"),
                    ("revision_required", "Revision requested"),
                    ("revised_submitted", "Revised paper submitted"),
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
