# Generated for revision re-review workflow
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0032_review_commented_paper_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="review_round",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Content review round for this review. Initial submission is round 0; author revisions use round 1, 2, etc.",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="review",
            unique_together={("submission", "reviewer", "review_round")},
        ),
    ]
