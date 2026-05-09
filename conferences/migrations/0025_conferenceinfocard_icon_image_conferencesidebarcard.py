# Generated manually for GAF Conference Hub

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0024_submission_revision_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='conferenceinfocard',
            name='icon_image',
            field=models.ImageField(blank=True, help_text='Optional small image/icon shown next to the card title.', null=True, upload_to='conference_info_icons/'),
        ),
        migrations.CreateModel(
            name='ConferenceSidebarCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eyebrow', models.CharField(blank=True, max_length=80)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('icon_image', models.ImageField(blank=True, help_text='Optional small image/icon shown next to the sidebar card title.', null=True, upload_to='conference_sidebar_icons/')),
                ('order', models.PositiveIntegerField(default=0)),
                ('enabled', models.BooleanField(default=True)),
                ('conference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sidebar_cards', to='conferences.conference')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
    ]
