from django.contrib import admin

from .models import (
    Conference,
    Submission,
    ConferenceRole,
    ReviewAssignment,
    EmailTemplate,
    EmailLog,
)


@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ("title_en", "start_date", "end_date", "submission_mode")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("title", "conference", "first_author", "first_author_email", "status", "created_at")
    search_fields = ("title", "first_author", "first_author_email", "coauthors", "coauthor_emails")


@admin.register(ConferenceRole)
class ConferenceRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "conference", "role")


@admin.register(ReviewAssignment)
class ReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ("submission", "reviewer", "role", "assigned_at")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("conference", "event", "enabled", "send_to_author", "send_to_coauthors")
    list_filter = ("conference", "event", "enabled")


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "conference", "event", "recipient", "status")
    list_filter = ("conference", "event", "status")
    search_fields = ("recipient", "subject", "message")
