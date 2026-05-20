from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0062_overview_customization_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='conference',
            name='overview_section_background',
            field=models.CharField(default='#f5f4ee', max_length=20),
        ),
        migrations.AddField(
            model_name='conference',
            name='overview_secondary_background',
            field=models.CharField(default='#ece8da', max_length=20),
        ),
    ]
