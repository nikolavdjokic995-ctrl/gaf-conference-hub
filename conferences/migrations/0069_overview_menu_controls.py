from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0068_remove_conference_hub_background_color_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='conference',
            name='overview_menu_left',
            field=models.PositiveIntegerField(default=18),
        ),
        migrations.AddField(
            model_name='conference',
            name='overview_menu_opacity',
            field=models.FloatField(default=0.28),
        ),
        migrations.AddField(
            model_name='conference',
            name='overview_menu_top',
            field=models.PositiveIntegerField(default=115),
        ),
    ]
