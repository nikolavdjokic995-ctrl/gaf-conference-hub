from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0053_use_local_file_storage"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="first_author_title",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="submission",
            name="coauthor_titles",
            field=models.TextField(blank=True, help_text="Enter co-author titles, one per line, in the same order as co-authors."),
        ),
    ]
