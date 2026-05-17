# Generated manually for UserProfile title and country fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0021_submission_secondary_topic"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="title",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="country",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
