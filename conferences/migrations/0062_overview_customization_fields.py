from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0061_alter_emailtemplate_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='conference',
            name='overview_menu_width',
            field=models.PositiveIntegerField(default=260),
        ),
        migrations.AddField(
            model_name='conference',
            name='overview_menu_background',
            field=models.CharField(default='#ffffff', max_length=20),
        ),
        migrations.AddField(
            model_name='conference',
            name='overview_content_width',
            field=models.PositiveIntegerField(default=1060),
        ),
        migrations.AddField(
            model_name='conference',
            name='overview_hero_height',
            field=models.PositiveIntegerField(default=560),
        ),
        migrations.AddField(
            model_name='conference',
            name='overview_card_background',
            field=models.CharField(default='#ffffff', max_length=20),
        ),
        migrations.AddField(
            model_name='conference',
            name='overview_text_color',
            field=models.CharField(default='#0b5d3b', max_length=20),
        ),
    ]
