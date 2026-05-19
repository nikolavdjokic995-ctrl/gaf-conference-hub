# Compatibility no-op migration.
# This file existed by mistake as 0024_submission_revision_workflow_fixed.py.
# It is kept empty so deployments do not try to add duplicate fields.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('conferences', '0052_submission_author_affiliation_orcid'),
    ]

    operations = []
