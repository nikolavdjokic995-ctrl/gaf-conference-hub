from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0039_limit_review_paper_classification"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="no_conflict_confirmed",
            field=models.BooleanField(
                default=False,
                help_text="Reviewer confirms there is no conflict of interest for this paper.",
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="extension_requested",
            field=models.BooleanField(
                default=False,
                help_text="Reviewer requests an extension of the review deadline.",
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="requested_deadline",
            field=models.DateField(
                blank=True,
                help_text="Requested new review deadline, if an extension is requested.",
                null=True,
            ),
        ),
    ]
