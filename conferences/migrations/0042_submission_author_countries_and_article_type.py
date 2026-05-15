# Generated patch for article type and author/co-author country statistics.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0041_submission_first_author_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="article_type",
            field=models.CharField(
                choices=[
                    ("research_paper", "Research paper"),
                    ("review_paper", "Review paper"),
                ],
                default="research_paper",
                help_text="Select whether this is a research paper or a review paper.",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="first_author_country",
            field=models.CharField(
                blank=True,
                help_text="Country of the first author.",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="coauthor_countries",
            field=models.TextField(
                blank=True,
                help_text="Enter co-author countries, one per line, in the same order as co-authors.",
            ),
        ),
    ]
