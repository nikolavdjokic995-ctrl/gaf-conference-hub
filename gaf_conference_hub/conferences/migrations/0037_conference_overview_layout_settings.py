# Generated manually for overview page layout settings.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0036_conferencefooterpartner_partner_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="conference",
            name="overview_section_padding",
            field=models.PositiveIntegerField(default=40),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_section_radius",
            field=models.PositiveIntegerField(default=26),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_grid_min_width",
            field=models.PositiveIntegerField(default=280),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_grid_gap",
            field=models.PositiveIntegerField(default=26),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_card_padding",
            field=models.PositiveIntegerField(default=28),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_card_radius",
            field=models.PositiveIntegerField(default=20),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_card_title_size",
            field=models.PositiveIntegerField(default=20),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_card_text_size",
            field=models.PositiveIntegerField(default=16),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_stats_card_padding",
            field=models.PositiveIntegerField(default=28),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_stats_card_radius",
            field=models.PositiveIntegerField(default=22),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_stats_number_size",
            field=models.PositiveIntegerField(default=38),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_stats_label_size",
            field=models.PositiveIntegerField(default=15),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_about_padding",
            field=models.PositiveIntegerField(default=38),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_about_radius",
            field=models.PositiveIntegerField(default=24),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_about_title_size",
            field=models.PositiveIntegerField(default=42),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_about_text_size",
            field=models.PositiveIntegerField(default=18),
        ),
    ]
