from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0040_review_conflict_deadline_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="first_author_email",
            field=models.EmailField(
                blank=True,
                help_text="Email address of the first author. This may be different from the account submitting the paper.",
                max_length=254,
            ),
        ),
    ]
