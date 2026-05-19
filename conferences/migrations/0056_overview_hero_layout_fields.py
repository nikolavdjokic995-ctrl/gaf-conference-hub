from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0053_use_local_file_storage"),
    ]

    operations = [
        migrations.AddField(
            model_name="conference",
            name="overview_hero_image_height",
            field=models.PositiveIntegerField(default=620),
        ),
        migrations.AddField(
            model_name="conference",
            name="overview_hero_buttons_margin_top",
            field=models.IntegerField(default=26),
        ),
    ]
