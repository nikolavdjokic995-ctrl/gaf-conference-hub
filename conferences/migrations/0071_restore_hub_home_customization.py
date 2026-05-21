# Generated manually to restore Hub home page customization fields.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0070_paper_revision_completed_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='conference',
            name='hub_background_image',
            field=models.ImageField(blank=True, help_text='Custom background image for the main Hub landing page.', null=True, upload_to='conference_hub_backgrounds/'),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_background_color',
            field=models.CharField(default='#f4f1e6', help_text='Background colour of the main Hub landing page.', max_length=20),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_header_background',
            field=models.CharField(default='#13365c', help_text='Header background colour on the main Hub landing page.', max_length=20),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_card_background',
            field=models.CharField(default='#ffffff', help_text='Conference card background colour on the main Hub landing page.', max_length=20),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_title_color',
            field=models.CharField(default='#0f3d2e', help_text='Main heading and conference title colour on the Hub landing page.', max_length=20),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_text_color',
            field=models.CharField(default='#374151', help_text='Main text colour on the Hub landing page.', max_length=20),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_container_width',
            field=models.PositiveIntegerField(default=880, help_text='Content/card area width on the Hub landing page in pixels.'),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_left_margin',
            field=models.PositiveIntegerField(default=200, help_text='Left margin of the Hub content/card area in pixels.'),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_background_image_width',
            field=models.PositiveIntegerField(default=100, help_text='Background image zoom/width percentage. Lower values show more of the image.'),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_background_image_opacity',
            field=models.FloatField(default=1, help_text='Background image opacity from 0 to 1.'),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_logo_width',
            field=models.PositiveIntegerField(default=140, help_text='Logo width inside the Hub conference card in pixels.'),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_card_radius',
            field=models.PositiveIntegerField(default=18, help_text='Hub conference card corner radius in pixels.'),
        ),
        migrations.AddField(
            model_name='conference',
            name='hub_card_padding',
            field=models.PositiveIntegerField(default=28, help_text='Hub conference card inner spacing in pixels.'),
        ),
    ]
