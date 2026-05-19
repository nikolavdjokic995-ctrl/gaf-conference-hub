# Generated manually for author affiliation and ORCID fields.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0051_remove_submission_coauthors_data_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="first_author_affiliation",
            field=models.CharField(blank=True, help_text="Affiliation of the first author.", max_length=255),
        ),
        migrations.AddField(
            model_name="submission",
            name="first_author_orcid",
            field=models.CharField(blank=True, help_text="ORCID iD of the first author.", max_length=50),
        ),
        migrations.AddField(
            model_name="submission",
            name="coauthor_affiliations",
            field=models.TextField(blank=True, help_text="Enter co-author affiliations, one per line, in the same order as co-authors."),
        ),
        migrations.AddField(
            model_name="submission",
            name="coauthor_orcids",
            field=models.TextField(blank=True, help_text="Enter co-author ORCID iDs, one per line, in the same order as co-authors."),
        ),
        migrations.AlterField(
            model_name="submission",
            name="abstract",
            field=models.TextField(help_text="Write the abstract directly in this field. Maximum 300 words."),
        ),
    ]
