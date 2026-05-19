# Generated manually for Cloudflare R2 document storage.

from django.db import migrations, models
import conferences.storage_backends


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0043_review_assignment_invitation_workflow'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='full_paper_file',
            field=models.FileField(blank=True, null=True, storage=conferences.storage_backends.HybridDocumentStorage(), upload_to='papers/'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='revised_paper_file',
            field=models.FileField(blank=True, null=True, storage=conferences.storage_backends.HybridDocumentStorage(), upload_to='revised_papers/'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='layout_revised_paper_file',
            field=models.FileField(blank=True, null=True, storage=conferences.storage_backends.HybridDocumentStorage(), upload_to='layout_revised_papers/'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='final_publication_file',
            field=models.FileField(blank=True, help_text='Final print-ready paper uploaded by the layout reviewer.', null=True, storage=conferences.storage_backends.HybridDocumentStorage(), upload_to='final_publication_papers/'),
        ),
        migrations.AlterField(
            model_name='submission',
            name='anonymized_paper_file',
            field=models.FileField(blank=True, null=True, storage=conferences.storage_backends.HybridDocumentStorage(), upload_to='anonymous_papers/'),
        ),
        migrations.AlterField(
            model_name='review',
            name='commented_paper_file',
            field=models.FileField(blank=True, help_text='Optional reviewer-uploaded paper with comments for the author.', null=True, storage=conferences.storage_backends.HybridDocumentStorage(), upload_to='reviewer_commented_papers/'),
        ),
        migrations.AlterField(
            model_name='conferenceinfocard',
            name='file',
            field=models.FileField(blank=True, null=True, storage=conferences.storage_backends.HybridDocumentStorage(), upload_to='conference_files/'),
        ),
    ]
