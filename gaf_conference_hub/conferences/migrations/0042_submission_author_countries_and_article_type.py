from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0041_submission_first_author_email"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE conferences_submission "
                        "ADD COLUMN IF NOT EXISTS article_type varchar(30) "
                        "NOT NULL DEFAULT 'research_paper';"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE conferences_submission "
                        "ADD COLUMN IF NOT EXISTS first_author_country varchar(100) "
                        "NOT NULL DEFAULT '';"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE conferences_submission "
                        "ADD COLUMN IF NOT EXISTS coauthor_countries text "
                        "NOT NULL DEFAULT '';"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
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
                        default="",
                        help_text="Country of the first author.",
                        max_length=100,
                    ),
                ),
                migrations.AddField(
                    model_name="submission",
                    name="coauthor_countries",
                    field=models.TextField(
                        blank=True,
                        default="",
                        help_text="Enter co-author countries, one per line, in the same order as co-authors.",
                    ),
                ),
            ],
        ),
    ]
