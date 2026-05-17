from django.db import migrations, models


def add_missing_overview_fields(apps, schema_editor):
    Conference = apps.get_model("conferences", "Conference")

    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            Conference._meta.db_table
        )
    }

    fields = [
        ("overview_section_padding", models.PositiveIntegerField(default=20)),
        ("overview_section_radius", models.PositiveIntegerField(default=26)),
        ("overview_grid_min_width", models.PositiveIntegerField(default=320)),
        ("overview_grid_gap", models.PositiveIntegerField(default=26)),
        ("overview_card_padding", models.PositiveIntegerField(default=28)),
        ("overview_card_radius", models.PositiveIntegerField(default=20)),
        ("overview_card_title_size", models.PositiveIntegerField(default=20)),
        ("overview_card_text_size", models.PositiveIntegerField(default=15)),
        ("overview_stats_card_padding", models.PositiveIntegerField(default=28)),
        ("overview_stats_card_radius", models.PositiveIntegerField(default=20)),
        ("overview_stats_number_size", models.PositiveIntegerField(default=42)),
        ("overview_stats_label_size", models.PositiveIntegerField(default=15)),
        ("overview_about_padding", models.PositiveIntegerField(default=34)),
        ("overview_about_radius", models.PositiveIntegerField(default=22)),
        ("overview_about_title_size", models.PositiveIntegerField(default=52)),
        ("overview_about_text_size", models.PositiveIntegerField(default=18)),
    ]

    for name, field in fields:
        if name not in existing_columns:
            field.set_attributes_from_name(name)
            schema_editor.add_field(Conference, field)


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0046_force_review_assignment_invitation_fields"),
    ]

    operations = [
        migrations.RunPython(add_missing_overview_fields, migrations.RunPython.noop),
    ]