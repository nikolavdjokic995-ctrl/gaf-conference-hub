# Generated patch for redesigned reviewer form and article type selection.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0037_conference_overview_layout_settings"),
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
            model_name="review",
            name="quality_originality",
            field=models.CharField(
                choices=[("poor", "Poor"), ("normal", "Normal"), ("good", "Good"), ("excellent", "Excellent")],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="quality_scientific_contribution",
            field=models.CharField(
                choices=[("poor", "Poor"), ("normal", "Normal"), ("good", "Good"), ("excellent", "Excellent")],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="quality_methodological_approach",
            field=models.CharField(
                choices=[("poor", "Poor"), ("normal", "Normal"), ("good", "Good"), ("excellent", "Excellent")],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="quality_references",
            field=models.CharField(
                choices=[("poor", "Poor"), ("normal", "Normal"), ("good", "Good"), ("excellent", "Excellent")],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="quality_clarity_expression",
            field=models.CharField(
                choices=[("poor", "Poor"), ("normal", "Normal"), ("good", "Good"), ("excellent", "Excellent")],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="paper_classification",
            field=models.CharField(
                choices=[
                    ("review_paper", "Review paper"),
                    ("research_paper", "Research paper"),
                    ("preliminary_report", "Preliminary report/Short communication"),
                    ("professional_paper", "Professional paper"),
                    ("none", "None of above"),
                ],
                default="research_paper",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="reviewer_competency",
            field=models.CharField(
                choices=[("poor", "Poor"), ("normal", "Normal"), ("good", "Good"), ("excellent", "Excellent")],
                default="normal",
                max_length=20,
            ),
        ),
    ]
