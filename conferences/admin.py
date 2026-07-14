from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Conference,
    Submission,
    ConferenceRole,
    ReviewAssignment,
    Review,
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


class ReviewAssignmentAdminForm(forms.ModelForm):
    """
    Admin form that exposes the latest Review connected to this assignment.

    Review data are deliberately separated into individual fields so an
    administrator can edit or clear one item without resetting the rest.
    """

    review_round = forms.IntegerField(
        required=False,
        disabled=True,
        label="Review round",
    )

    no_conflict_confirmed = forms.BooleanField(
        required=False,
        label="No conflict of interest confirmed",
    )
    extension_requested = forms.BooleanField(
        required=False,
        label="Deadline extension requested",
    )
    requested_deadline = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Requested deadline",
    )

    quality_originality = forms.ChoiceField(
        required=False,
        choices=Review.QUALITY_CHOICES,
        label="Originality of the topic",
    )
    quality_scientific_contribution = forms.ChoiceField(
        required=False,
        choices=Review.QUALITY_CHOICES,
        label="Scientific contribution",
    )
    quality_methodological_approach = forms.ChoiceField(
        required=False,
        choices=Review.QUALITY_CHOICES,
        label="Methodological approach",
    )
    quality_references = forms.ChoiceField(
        required=False,
        choices=Review.QUALITY_CHOICES,
        label="Quality of references",
    )
    quality_clarity_expression = forms.ChoiceField(
        required=False,
        choices=Review.QUALITY_CHOICES,
        label="Clarity in expression",
    )
    paper_classification = forms.ChoiceField(
        required=False,
        choices=Review.PAPER_CLASSIFICATION_CHOICES,
        label="Paper classification",
    )
    reviewer_competency = forms.ChoiceField(
        required=False,
        choices=Review.QUALITY_CHOICES,
        label="Reviewer competency",
    )

    comments_for_authors = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        label="Comments to authors",
    )
    comments_for_editors = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 7}),
        label="Confidential comments to editors",
    )
    overall_recommendation = forms.ChoiceField(
        required=False,
        choices=Review.RECOMMENDATION_CHOICES,
        label="Overall recommendation",
    )
    wants_final_notification = forms.ChoiceField(
        required=False,
        choices=Review.YES_NO_CHOICES,
        label="Notify reviewer about final decision",
    )

    commented_paper_file = forms.FileField(
        required=False,
        label="Upload replacement review file",
        help_text="Uploading a new file replaces the current reviewer file only.",
    )
    clear_commented_paper_file = forms.BooleanField(
        required=False,
        label="Delete current review file",
        help_text="Deletes only the uploaded review file. Checklist, comments and recommendation remain unchanged.",
    )

    # Legacy/internal fields are exposed separately for exceptional corrections.
    content_context = forms.ChoiceField(required=False, choices=Review.AUTHOR_SCALE_CHOICES)
    research_design = forms.ChoiceField(required=False, choices=Review.AUTHOR_SCALE_CHOICES)
    arguments_discussion = forms.ChoiceField(required=False, choices=Review.AUTHOR_SCALE_CHOICES)
    results_presented = forms.ChoiceField(required=False, choices=Review.AUTHOR_SCALE_CHOICES)
    references_adequate = forms.ChoiceField(required=False, choices=Review.AUTHOR_SCALE_CHOICES)
    conclusions_supported = forms.ChoiceField(required=False, choices=Review.AUTHOR_SCALE_CHOICES)
    english_quality = forms.ChoiceField(required=False, choices=Review.ENGLISH_CHOICES)
    conflict_of_interest = forms.ChoiceField(required=False, choices=Review.YES_NO_CHOICES)
    plagiarism_detected = forms.ChoiceField(required=False, choices=Review.YES_NO_CHOICES)
    inappropriate_self_citations = forms.ChoiceField(required=False, choices=Review.YES_NO_CHOICES)
    ethical_concerns = forms.ChoiceField(required=False, choices=Review.YES_NO_CHOICES)
    originality = forms.ChoiceField(required=False, choices=Review.RATING_CHOICES)
    contribution = forms.ChoiceField(required=False, choices=Review.RATING_CHOICES)
    structure_clarity = forms.ChoiceField(required=False, choices=Review.RATING_CHOICES)
    logical_coherence = forms.ChoiceField(required=False, choices=Review.RATING_CHOICES)
    engagement_sources = forms.ChoiceField(required=False, choices=Review.RATING_CHOICES)
    overall_merit = forms.ChoiceField(required=False, choices=Review.RATING_CHOICES)
    references_relevant = forms.ChoiceField(required=False, choices=Review.YES_NO_CHOICES)

    REVIEW_FIELD_NAMES = (
        "no_conflict_confirmed",
        "extension_requested",
        "requested_deadline",
        "quality_originality",
        "quality_scientific_contribution",
        "quality_methodological_approach",
        "quality_references",
        "quality_clarity_expression",
        "paper_classification",
        "reviewer_competency",
        "comments_for_authors",
        "comments_for_editors",
        "overall_recommendation",
        "wants_final_notification",
        "content_context",
        "research_design",
        "arguments_discussion",
        "results_presented",
        "references_adequate",
        "conclusions_supported",
        "english_quality",
        "conflict_of_interest",
        "plagiarism_detected",
        "inappropriate_self_citations",
        "ethical_concerns",
        "originality",
        "contribution",
        "structure_clarity",
        "logical_coherence",
        "engagement_sources",
        "overall_merit",
        "references_relevant",
    )

    class Meta:
        model = ReviewAssignment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.review = None

        if self.instance and self.instance.pk:
            self.review = (
                Review.objects.filter(
                    submission=self.instance.submission,
                    reviewer=self.instance.reviewer,
                )
                .order_by("-review_round", "-updated_at", "-pk")
                .first()
            )

        if self.review:
            self.fields["review_round"].initial = self.review.review_round
            for field_name in self.REVIEW_FIELD_NAMES:
                self.fields[field_name].initial = getattr(self.review, field_name)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("clear_commented_paper_file") and cleaned.get("commented_paper_file"):
            self.add_error(
                "commented_paper_file",
                "Choose either a replacement file or 'Delete current review file', not both.",
            )
        return cleaned

    def save_related_review(self):
        related_names = set(self.REVIEW_FIELD_NAMES) | {
            "commented_paper_file",
            "clear_commented_paper_file",
        }
        changed_review_fields = related_names.intersection(self.changed_data)

        if not changed_review_fields:
            return self.review

        review = self.review
        if review is None:
            review = Review(
                submission=self.instance.submission,
                reviewer=self.instance.reviewer,
                review_round=0,
            )

        for field_name in self.REVIEW_FIELD_NAMES:
            if field_name in self.cleaned_data:
                value = self.cleaned_data.get(field_name)
                # Keep model defaults when an empty optional choice is submitted
                # for a newly-created review.
                if value not in ("", None) or review.pk:
                    setattr(review, field_name, value)

        if self.cleaned_data.get("clear_commented_paper_file"):
            if review.commented_paper_file:
                review.commented_paper_file.delete(save=False)
            review.commented_paper_file = None
        elif self.cleaned_data.get("commented_paper_file"):
            if review.commented_paper_file:
                review.commented_paper_file.delete(save=False)
            review.commented_paper_file = self.cleaned_data["commented_paper_file"]

        review.save()
        self.review = review
        return review


@admin.register(ReviewAssignment)
class ReviewAssignmentAdmin(admin.ModelAdmin):
    form = ReviewAssignmentAdminForm

    list_display = (
        "submission",
        "reviewer",
        "role",
        "invitation_status",
        "review_state",
        "review_file_state",
        "assigned_at",
    )
    list_filter = (
        "role",
        "invitation_status",
        "due_soon_reminder_sent",
        "overdue_reminder_sent",
        "submission__conference",
    )
    search_fields = (
        "submission__paper_code",
        "submission__title",
        "reviewer__username",
        "reviewer__first_name",
        "reviewer__last_name",
        "reviewer__email",
    )
    autocomplete_fields = ("submission", "reviewer")
    date_hierarchy = "assigned_at"
    save_on_top = True

    readonly_fields = (
        "assigned_at",
        "current_review_file",
        "review_created_at",
        "review_updated_at",
        "review_auto_score",
    )

    fieldsets = (
        (
            "Assignment",
            {
                "fields": (
                    "submission",
                    "reviewer",
                    "role",
                    "assigned_at",
                )
            },
        ),
        (
            "Invitation status and deadlines",
            {
                "fields": (
                    "invitation_status",
                    "proposed_deadline",
                    "accepted_deadline",
                    "deadline_extension_requested",
                    "decline_reason",
                    "review_invitation_sent_at",
                    "accepted_at",
                    "declined_at",
                )
            },
        ),
        (
            "Reminder tracking",
            {
                "fields": (
                    "due_soon_reminder_sent",
                    "overdue_reminder_sent",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Current review — checklist",
            {
                "fields": (
                    "review_round",
                    "no_conflict_confirmed",
                    "extension_requested",
                    "requested_deadline",
                    "quality_originality",
                    "quality_scientific_contribution",
                    "quality_methodological_approach",
                    "quality_references",
                    "quality_clarity_expression",
                    "paper_classification",
                    "reviewer_competency",
                ),
                "description": (
                    "Each checklist item is independent. Changing one item does not "
                    "alter comments, files, recommendation or assignment status."
                ),
            },
        ),
        (
            "Current review — comments and recommendation",
            {
                "fields": (
                    "comments_for_authors",
                    "comments_for_editors",
                    "overall_recommendation",
                    "wants_final_notification",
                    "review_auto_score",
                    "review_created_at",
                    "review_updated_at",
                )
            },
        ),
        (
            "Current review — uploaded file",
            {
                "fields": (
                    "current_review_file",
                    "commented_paper_file",
                    "clear_commented_paper_file",
                ),
                "description": (
                    "The existing file can be downloaded, replaced, or deleted "
                    "without changing any other review data."
                ),
            },
        ),
        (
            "Advanced / legacy review fields",
            {
                "fields": (
                    "content_context",
                    "research_design",
                    "arguments_discussion",
                    "results_presented",
                    "references_adequate",
                    "conclusions_supported",
                    "english_quality",
                    "conflict_of_interest",
                    "plagiarism_detected",
                    "inappropriate_self_citations",
                    "ethical_concerns",
                    "originality",
                    "contribution",
                    "structure_clarity",
                    "logical_coherence",
                    "engagement_sources",
                    "overall_merit",
                    "references_relevant",
                ),
                "classes": ("collapse",),
                "description": (
                    "Use only for exceptional corrections to legacy/internal values."
                ),
            },
        ),
    )

    def _latest_review(self, obj):
        return (
            Review.objects.filter(
                submission=obj.submission,
                reviewer=obj.reviewer,
            )
            .order_by("-review_round", "-updated_at", "-pk")
            .first()
        )

    @admin.display(description="Review")
    def review_state(self, obj):
        review = self._latest_review(obj)
        if not review:
            return "Not submitted"
        return f"Round {review.review_round} — {review.get_overall_recommendation_display()}"

    @admin.display(description="Review file")
    def review_file_state(self, obj):
        review = self._latest_review(obj)
        if review and review.commented_paper_file:
            return "Uploaded"
        return "None"

    @admin.display(description="Current review file")
    def current_review_file(self, obj):
        if not obj or not obj.pk:
            return "No review assignment saved yet."
        review = self._latest_review(obj)
        if not review or not review.commented_paper_file:
            return "No file uploaded."
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Download current file: {}</a>',
            review.commented_paper_file.url,
            review.commented_paper_file.name.rsplit("/", 1)[-1],
        )

    @admin.display(description="Review created at")
    def review_created_at(self, obj):
        review = self._latest_review(obj) if obj and obj.pk else None
        return review.created_at if review else "—"

    @admin.display(description="Review updated at")
    def review_updated_at(self, obj):
        review = self._latest_review(obj) if obj and obj.pk else None
        return review.updated_at if review else "—"

    @admin.display(description="Automatic score")
    def review_auto_score(self, obj):
        review = self._latest_review(obj) if obj and obj.pk else None
        return review.auto_score if review else "—"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        form.instance = obj
        form.save_related_review()


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Direct Review administration is also available for full audit/control.
    Every field remains independent and Django provides a separate Clear
    checkbox for the uploaded file.
    """

    list_display = (
        "submission",
        "reviewer",
        "review_round",
        "overall_recommendation",
        "auto_score",
        "has_uploaded_file",
        "updated_at",
    )
    list_filter = (
        "review_round",
        "overall_recommendation",
        "paper_classification",
        "quality_originality",
        "quality_scientific_contribution",
        "submission__conference",
    )
    search_fields = (
        "submission__paper_code",
        "submission__title",
        "reviewer__username",
        "reviewer__first_name",
        "reviewer__last_name",
        "reviewer__email",
        "comments_for_authors",
        "comments_for_editors",
    )
    autocomplete_fields = ("submission", "reviewer")
    readonly_fields = ("auto_score", "created_at", "updated_at")
    save_on_top = True

    fieldsets = (
        (
            "Review identity",
            {
                "fields": (
                    "submission",
                    "reviewer",
                    "review_round",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Current checklist",
            {
                "fields": (
                    "no_conflict_confirmed",
                    "extension_requested",
                    "requested_deadline",
                    "quality_originality",
                    "quality_scientific_contribution",
                    "quality_methodological_approach",
                    "quality_references",
                    "quality_clarity_expression",
                    "paper_classification",
                    "reviewer_competency",
                )
            },
        ),
        (
            "Comments and recommendation",
            {
                "fields": (
                    "comments_for_authors",
                    "comments_for_editors",
                    "overall_recommendation",
                    "wants_final_notification",
                    "auto_score",
                )
            },
        ),
        (
            "Reviewer file",
            {
                "fields": ("commented_paper_file",),
                "description": (
                    "Use the built-in Clear checkbox to delete only this file, "
                    "or upload a replacement. No other review data are changed."
                ),
            },
        ),
        (
            "Advanced / legacy evaluation fields",
            {
                "fields": (
                    "content_context",
                    "research_design",
                    "arguments_discussion",
                    "results_presented",
                    "references_adequate",
                    "conclusions_supported",
                    "english_quality",
                    "conflict_of_interest",
                    "plagiarism_detected",
                    "inappropriate_self_citations",
                    "ethical_concerns",
                    "originality",
                    "contribution",
                    "structure_clarity",
                    "logical_coherence",
                    "engagement_sources",
                    "overall_merit",
                    "references_relevant",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(boolean=True, description="File")
    def has_uploaded_file(self, obj):
        return bool(obj.commented_paper_file)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("conference", "event", "enabled", "send_to_author", "send_to_coauthors")
    list_filter = ("conference", "event", "enabled")


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "conference", "event", "recipient", "status")
    list_filter = ("conference", "event", "status")
    search_fields = ("recipient", "subject", "message")
