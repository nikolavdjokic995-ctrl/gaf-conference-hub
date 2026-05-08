# Generated manually for submission abstract and keywords fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0022_userprofile_title_country"),
    ]

    operations = [
        migrations.AlterField(
            model_name="submission",
            name="abstract",
            field=models.TextField(
                help_text="Write the abstract directly in this field. Maximum 2500 characters.",
                max_length=2500,
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="keywords",
            field=models.CharField(
                default="",
                help_text="Enter keywords separated by commas.",
                max_length=255,
            ),
            preserve_default=False,
        ),
    ]
