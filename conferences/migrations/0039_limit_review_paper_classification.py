from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0038_review_form_redesign"),
    ]

    operations = [
        migrations.AlterField(
            model_name="review",
            name="paper_classification",
            field=models.CharField(
                choices=[
                    ("review_paper", "Review paper"),
                    ("research_paper", "Research paper"),
                ],
                default="research_paper",
                max_length=30,
            ),
        ),
    ]
