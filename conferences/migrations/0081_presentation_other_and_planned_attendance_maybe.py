from django.db import migrations, models


def copy_planned_attendance_forward(apps, schema_editor):
    SubmissionParticipant = apps.get_model("conferences", "SubmissionParticipant")
    for link in SubmissionParticipant.objects.all().only("id", "planned_attendance", "planned_attendance_choice"):
        if link.planned_attendance is True:
            link.planned_attendance_choice = "yes"
        elif link.planned_attendance is False:
            link.planned_attendance_choice = "no"
        else:
            link.planned_attendance_choice = None
        link.save(update_fields=["planned_attendance_choice"])


def copy_planned_attendance_reverse(apps, schema_editor):
    SubmissionParticipant = apps.get_model("conferences", "SubmissionParticipant")
    for link in SubmissionParticipant.objects.all().only("id", "planned_attendance", "planned_attendance_choice"):
        if link.planned_attendance_choice == "yes":
            link.planned_attendance = True
        elif link.planned_attendance_choice == "no":
            link.planned_attendance = False
        else:
            link.planned_attendance = None
        link.save(update_fields=["planned_attendance"])


def migrate_legacy_not_presenting(apps, schema_editor):
    SubmissionParticipation = apps.get_model("conferences", "SubmissionParticipation")
    SubmissionParticipation.objects.filter(presentation_type="not_presenting").update(
        presentation_type="other",
        other_presentation_details=(
            "I will not present this paper (response submitted before the presentation options were updated)."
        ),
    )


def reverse_legacy_not_presenting(apps, schema_editor):
    SubmissionParticipation = apps.get_model("conferences", "SubmissionParticipation")
    SubmissionParticipation.objects.filter(
        presentation_type="other",
        other_presentation_details=(
            "I will not present this paper (response submitted before the presentation options were updated)."
        ),
    ).update(
        presentation_type="not_presenting",
        other_presentation_details="",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0080_participation_and_attendance"),
    ]

    operations = [
        migrations.AddField(
            model_name="submissionparticipation",
            name="other_presentation_details",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="submissionparticipant",
            name="planned_attendance_choice",
            field=models.CharField(
                blank=True,
                choices=[("yes", "Yes"), ("maybe", "Maybe"), ("no", "No")],
                max_length=10,
                null=True,
            ),
        ),
        migrations.RunPython(
            copy_planned_attendance_forward,
            copy_planned_attendance_reverse,
        ),
        migrations.RemoveField(
            model_name="submissionparticipant",
            name="planned_attendance",
        ),
        migrations.RenameField(
            model_name="submissionparticipant",
            old_name="planned_attendance_choice",
            new_name="planned_attendance",
        ),
        migrations.AlterField(
            model_name="submissionparticipation",
            name="presentation_type",
            field=models.CharField(
                blank=True,
                choices=[("oral", "Oral presentation"), ("poster", "Poster presentation"), ("other", "Other")],
                max_length=30,
            ),
        ),
        migrations.RunPython(
            migrate_legacy_not_presenting,
            reverse_legacy_not_presenting,
        ),
    ]
