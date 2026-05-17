# Generated for reviewer commented-file workflow.

import cloudinary_storage.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0031_alter_conferenceinfocard_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="commented_paper_file",
            field=models.FileField(
                blank=True,
                help_text="Optional reviewer-uploaded paper with comments for the author.",
                null=True,
                storage=cloudinary_storage.storage.RawMediaCloudinaryStorage(),
                upload_to="reviewer_commented_papers/",
            ),
        ),
    ]
