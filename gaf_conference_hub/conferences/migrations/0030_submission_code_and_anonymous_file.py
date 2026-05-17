from django.db import migrations, models
import cloudinary_storage.storage


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0029_alter_emailtemplate_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="paper_code",
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="anonymized_paper_file",
            field=models.FileField(blank=True, null=True, storage=cloudinary_storage.storage.RawMediaCloudinaryStorage(), upload_to="anonymous_papers/"),
        ),
    ]
