from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0079_remove_conference_hub_background_color_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConferenceParticipant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("title", models.CharField(blank=True, max_length=80)),
                ("affiliation", models.CharField(blank=True, max_length=255)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("normalized_email", models.CharField(blank=True, db_index=True, max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("conference", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participants", to="conferences.conference")),
            ],
            options={"ordering": ["name", "email"]},
        ),
        migrations.CreateModel(
            name="SubmissionParticipation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("participation_request_sent_at", models.DateTimeField(blank=True, null=True)),
                ("participation_request_subject", models.CharField(blank=True, max_length=255)),
                ("participation_request_body", models.TextField(blank=True)),
                ("participation_response_open", models.BooleanField(default=False)),
                ("presentation_type", models.CharField(blank=True, choices=[("not_presenting", "I will not present this paper"), ("oral", "Oral presentation"), ("poster", "Poster presentation")], max_length=30)),
                ("presentation_file", models.FileField(blank=True, max_length=500, null=True, upload_to="conference_presentations/")),
                ("comments", models.TextField(blank=True)),
                ("participation_submitted_at", models.DateTimeField(blank=True, null=True)),
                ("final_confirmation_request_sent_at", models.DateTimeField(blank=True, null=True)),
                ("final_confirmation_subject", models.CharField(blank=True, max_length=255)),
                ("final_confirmation_body", models.TextField(blank=True)),
                ("final_confirmation_response_open", models.BooleanField(default=False)),
                ("final_confirmation_submitted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("submission", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="participation", to="conferences.submission")),
            ],
        ),
        migrations.CreateModel(
            name="SubmissionParticipant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("author_order", models.PositiveSmallIntegerField(default=1)),
                ("is_first_author", models.BooleanField(default=False)),
                ("planned_attendance", models.BooleanField(blank=True, null=True)),
                ("confirmed_attendance", models.BooleanField(blank=True, null=True)),
                ("participant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submission_links", to="conferences.conferenceparticipant")),
                ("submission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participation_authors", to="conferences.submission")),
            ],
            options={"ordering": ["author_order"]},
        ),
        migrations.AddConstraint(
            model_name="conferenceparticipant",
            constraint=models.UniqueConstraint(condition=~models.Q(normalized_email=""), fields=("conference", "normalized_email"), name="unique_conference_participant_email"),
        ),
        migrations.AddConstraint(
            model_name="submissionparticipant",
            constraint=models.UniqueConstraint(fields=("submission", "author_order"), name="unique_submission_author_order"),
        ),
    ]
