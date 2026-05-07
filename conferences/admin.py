from django.contrib import admin
from .models import Conference, Submission, ConferenceRole


@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ("title_en", "start_date", "end_date", "submission_mode")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("title", "conference", "status", "created_at")


@admin.register(ConferenceRole)
class ConferenceRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "conference", "role")

from .models import ReviewAssignment
admin.site.register(ReviewAssignment)

from .models import EmailTemplate

admin.site.register(EmailTemplate)