# Generated manually for revision and layout review workflow

import cloudinary_storage.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0023_submission_abstract_keywords'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='judge_revision_message',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='submission',
            name='layout_revision_message',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='submission',
            name='revision_round',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='submission',
            name='layout_revision_round',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='submission',
            name='revised_paper_file',
            field=models.FileField(blank=True, null=True, storage=cloudinary_storage.storage.RawMediaCloudinaryStorage(), upload_to='revised_papers/'),
        ),
        migrations.AddField(
            model_name='submission',
            name='layout_revised_paper_file',
            field=models.FileField(blank=True, null=True, storage=cloudinary_storage.storage.RawMediaCloudinaryStorage(), upload_to='layout_revised_papers/'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='status',
            field=models.CharField(choices=[('submitted', 'Submitted'), ('under_review', 'Under content review'), ('revision_required', 'Revision requested'), ('revised_submitted', 'Revised paper submitted'), ('accepted_for_layout', 'Accepted for layout review'), ('layout_revision_required', 'Layout corrections requested'), ('layout_revision_submitted', 'Layout corrected paper submitted'), ('final_accepted', 'Final accepted'), ('accepted', 'Accepted (legacy)'), ('rejected', 'Rejected')], default='submitted', max_length=30),
        ),
    ]
