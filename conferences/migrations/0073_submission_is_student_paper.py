# Generated manually for GAF Conference Hub

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0072_alter_submission_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="is_student_paper",
            field=models.BooleanField(
                default=False,
                help_text="Mark whether this manuscript is submitted for the PhD/student session.",
                verbose_name="Student paper",
            ),
        ),
    ]
