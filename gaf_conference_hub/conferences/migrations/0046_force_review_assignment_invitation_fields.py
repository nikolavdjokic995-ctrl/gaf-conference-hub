from django.db import migrations, models


def add_missing_review_assignment_fields(apps, schema_editor):
    ReviewAssignment = apps.get_model("conferences", "ReviewAssignment")

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                ReviewAssignment._meta.db_table
            )
        }

    fields_to_add = [
        ("invitation_status", models.CharField(max_length=20, default="pending")),
        ("proposed_deadline", models.DateField(null=True, blank=True)),
        ("accepted_deadline", models.DateField(null=True, blank=True)),
        ("deadline_extension_requested", models.BooleanField(default=False)),
        ("decline_reason", models.TextField(blank=True, default="")),
        ("review_invitation_sent_at", models.DateTimeField(null=True, blank=True)),
        ("accepted_at", models.DateTimeField(null=True, blank=True)),
        ("declined_at", models.DateTimeField(null=True, blank=True)),
        ("due_soon_reminder_sent", models.BooleanField(default=False)),
        ("overdue_reminder_sent", models.BooleanField(default=False)),
    ]

    for field_name, field in fields_to_add:
        if field_name not in existing_columns:
            field.set_attributes_from_name(field_name)
            schema_editor.add_field(ReviewAssignment, field)


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0045_alter_emailtemplate_event_and_more"),
    ]

    operations = [
        migrations.RunPython(add_missing_review_assignment_fields, migrations.RunPython.noop),
    ]
