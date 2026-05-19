# Generated to remove custom R2 storage from file fields and use default local storage.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0024_submission_revision_workflow_fixed'),
    ]

    operations = [
        migrations.AlterField(
            model_name="submission",
            name="full_paper_file",
            field=models.FileField(blank=True, max_length=500, null=True, upload_to="papers/"),
        ),
        migrations.AlterField(
            model_name="submission",
            name="original_submission_file",
            field=models.FileField(blank=True, max_length=500, null=True, upload_to="original_submission_papers/"),
        ),
        migrations.AlterField(
            model_name="submission",
            name="revised_paper_file",
            field=models.FileField(blank=True, max_length=500, null=True, upload_to="revised_papers/"),
        ),
        migrations.AlterField(
            model_name="submission",
            name="layout_revised_paper_file",
            field=models.FileField(blank=True, max_length=500, null=True, upload_to="layout_revised_papers/"),
        ),
        migrations.AlterField(
            model_name="submission",
            name="final_publication_file",
            field=models.FileField(blank=True, help_text="Final print-ready paper uploaded by the layout reviewer.", max_length=500, null=True, upload_to="final_publication_papers/"),
        ),
        migrations.AlterField(
            model_name="submission",
            name="anonymized_paper_file",
            field=models.FileField(blank=True, max_length=500, null=True, upload_to="anonymous_papers/"),
        ),
        migrations.AlterField(
            model_name="review",
            name="commented_paper_file",
            field=models.FileField(blank=True, help_text="Optional reviewer-uploaded paper with comments for the author.", max_length=500, null=True, upload_to="reviewer_commented_papers/"),
        ),
        migrations.AlterField(
            model_name="conferenceinfocard",
            name="file",
            field=models.FileField(blank=True, max_length=500, null=True, upload_to="conference_files/"),
        ),
    ]
