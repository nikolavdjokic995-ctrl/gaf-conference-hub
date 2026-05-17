# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0013_conferencetopic"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="topic",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="submissions",
                to="conferences.conferencetopic",
            ),
        ),
        migrations.AddField(
            model_name="conferencerole",
            name="topics",
            field=models.ManyToManyField(
                blank=True,
                related_name="reviewer_roles",
                to="conferences.conferencetopic",
            ),
        ),
    ]