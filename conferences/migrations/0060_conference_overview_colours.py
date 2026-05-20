# Generated manually for overview colour settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0059_submission_coauthor_titles"),
    ]

    operations = [
        migrations.AddField(
            model_name="conference",
            name="overview_page_background_color",
            field=models.CharField(default="#f3f1e7", help_text="Background colour of the conference overview page.", max_length=20),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_hero_background_color",
            field=models.CharField(default="#f3f1e7", help_text="Background colour behind the hero image.", max_length=20),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_section_background_color",
            field=models.CharField(default="#ffffff", help_text="Background colour of the main overview content section.", max_length=20),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_card_background_color",
            field=models.CharField(default="#f9fafb", help_text="Background colour of overview information cards.", max_length=20),
        ),
    ]
