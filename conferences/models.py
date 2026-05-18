from django.db import models
from django.contrib.auth.models import User
from django.utils.html import strip_tags
from html import unescape
from cloudinary_storage.storage import RawMediaCloudinaryStorage
from .storage_backends import HybridDocumentStorage


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    affiliation = models.CharField(max_length=255)
    title = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, blank=True)

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}"
        return full_name.strip() or self.user.username

class Conference(models.Model):
    SUBMISSION_MODE_CHOICES = [
        ("full", "Full paper only"),
        ("abstract", "Abstract first, then full paper"),
    ]

    title_en = models.TextField()
    title_sr = models.TextField()
    slug = models.SlugField(unique=True)

    description_en = models.TextField(blank=True)
    description_sr = models.TextField(blank=True)

    start_date = models.DateField()
    end_date = models.DateField()

    submission_deadline = models.DateField(null=True, blank=True)
    review_deadline = models.DateField(null=True, blank=True)

    submission_mode = models.CharField(
        max_length=20,
        choices=SUBMISSION_MODE_CHOICES,
        default="full",
    )

    logo = models.ImageField(upload_to="conference_logos/", blank=True, null=True)

    TEMPLATE_CHOICES = [
        ("green", "Green Building"),
        ("modern", "Modern"),
        ("classic", "Classic"),
    ]

    template_style = models.CharField(
        max_length=20,
        choices=TEMPLATE_CHOICES,
        default="green"
    )

    hero_image = models.ImageField(
        upload_to="conference_hero/",
        blank=True,
        null=True
    )

    location = models.CharField(max_length=255, blank=True)
    registration_url = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    organizer = models.CharField(max_length=255, blank=True)
    
    footer_description = models.TextField(blank=True)

    footer_copyright = models.CharField(
        max_length=255,
        blank=True
    )

    footer_contact_email = models.EmailField(blank=True)

    footer_address = models.CharField(
        max_length=255,
        blank=True
    )

    footer_logo = models.ImageField(
        upload_to="conference_footer/",
        blank=True,
        null=True
    )

    # Overview page layout settings
    overview_section_padding = models.PositiveIntegerField(default=40)
    overview_section_radius = models.PositiveIntegerField(default=26)
    overview_grid_min_width = models.PositiveIntegerField(default=280)
    overview_grid_gap = models.PositiveIntegerField(default=26)
    overview_card_padding = models.PositiveIntegerField(default=28)
    overview_card_radius = models.PositiveIntegerField(default=20)
    overview_card_title_size = models.PositiveIntegerField(default=20)
    overview_card_text_size = models.PositiveIntegerField(default=16)
    overview_stats_card_padding = models.PositiveIntegerField(default=28)
    overview_stats_card_radius = models.PositiveIntegerField(default=22)
    overview_stats_number_size = models.PositiveIntegerField(default=38)
    overview_stats_label_size = models.PositiveIntegerField(default=15)
    overview_about_padding = models.PositiveIntegerField(default=38)
    overview_about_radius = models.PositiveIntegerField(default=24)
    overview_about_title_size = models.PositiveIntegerField(default=42)
    overview_about_text_size = models.PositiveIntegerField(default=18)


    @property
    def plain_title(self):
        title = strip_tags(self.title_en or "")
        title = unescape(title)
        title = title.replace("\xa0", " ")
        return " ".join(title.split())

    def __str__(self):
        return self.plain_title or self.title_en


class ConferenceTopic(models.Model):
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name="topics"
    )

    code = models.CharField(max_length=10)
    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

    class Meta:
        ordering = ["order", "code"]
        unique_together = ("conference", "code")


class Submission(models.Model):
    ARTICLE_TYPE_CHOICES = [
        ("research_paper", "Research paper"),
        ("review_paper", "Review paper"),
    ]

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("under_review", "Under content review"),
        ("revision_required", "Revision requested"),
        ("revised_submitted", "Revised paper submitted"),
        ("accepted_for_layout", "Accepted for layout review"),
        ("layout_revision_required", "Layout corrections requested"),
        ("layout_revision_submitted", "Layout corrected paper submitted"),
        ("final_accepted", "Final accepted"),
        ("accepted", "Accepted (legacy)"),
        ("rejected", "Rejected"),
    ]

    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    first_author = models.CharField(max_length=255)

    paper_code = models.CharField(max_length=50, blank=True, unique=True)

    article_type = models.CharField(
        max_length=30,
        choices=ARTICLE_TYPE_CHOICES,
        default="research_paper",
        help_text="Select whether this is a research paper or a review paper."
    )

    coauthors = models.TextField(
        blank=True,
        help_text="Separate co-authors with commas or new lines."
    )

    first_author_email = models.EmailField(
        blank=True,
        help_text="Email address of the first author. This can be different from the submitting user email."
    )

    first_author_country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Country of the first author."
    )

    coauthor_emails = models.TextField(
        blank=True,
        help_text="Enter co-author emails, one per line."
    )    

    coauthor_countries = models.TextField(
        blank=True,
        help_text="Enter co-author countries, one per line, in the same order as co-authors."
    )

    title = models.CharField(max_length=255)
    abstract = models.TextField(
        max_length=2500,
        help_text="Write the abstract directly in this field. Maximum 2500 characters."
    )
    keywords = models.CharField(
        max_length=255,
        help_text="Enter keywords separated by commas."
    )

    abstract_file = models.FileField(
        upload_to="abstracts/",
        blank=True,
        null=True,
        max_length=500
    )

    full_paper_file = models.FileField(
        upload_to="papers/",
        storage=HybridDocumentStorage(),
        blank=True,
        null=True,
        max_length=500

    )

    original_submission_file = models.FileField(
        upload_to="original_submission_papers/",
        storage=HybridDocumentStorage(),
        blank=True,
        null=True,
        max_length=500
    )

    topic = models.ForeignKey(
        ConferenceTopic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions"
    )
    secondary_topic = models.ForeignKey(
        ConferenceTopic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="secondary_submissions"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="submitted",
    )

    final_comment = models.TextField(blank=True)

    judge_revision_message = models.TextField(blank=True)
    layout_revision_message = models.TextField(blank=True)

    revision_round = models.PositiveSmallIntegerField(default=0)
    layout_revision_round = models.PositiveSmallIntegerField(default=0)

    revised_paper_file = models.FileField(
        upload_to="revised_papers/",
        storage=HybridDocumentStorage(),
        blank=True,
        null=True,
        max_length=500
    )

    layout_revised_paper_file = models.FileField(
        upload_to="layout_revised_papers/",
        storage=HybridDocumentStorage(),
        blank=True,
        null=True,
        max_length=500
    )

    final_publication_file = models.FileField(
        upload_to="final_publication_papers/",
        storage=HybridDocumentStorage(),
        blank=True,
        null=True,
        help_text="Final print-ready paper uploaded by the layout reviewer.",
        max_length=500
    )

    anonymized_paper_file = models.FileField(
        upload_to="anonymous_papers/",
        storage=HybridDocumentStorage(),
        blank=True,
        null=True,
        max_length=500
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def topic_list(self):
        topics = []

        if self.topic:
            topics.append(self.topic)

        if self.secondary_topic:
            topics.append(self.secondary_topic)

        return topics


    def original_author_file(self):
        """Return the preserved initial author submission if available."""
        return self.original_submission_file or self.full_paper_file

    def __str__(self):
        return self.title


class ConferenceRole(models.Model):
    ROLE_CHOICES = [
        ("manager", "Paper manager"),
        ("judge", "Judge"),
        ("content_reviewer", "Content reviewer"),
        ("layout_reviewer", "Layout reviewer"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name="roles"
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    topics = models.ManyToManyField(
        "ConferenceTopic",
        blank=True,
        related_name="reviewer_roles"
    )

    class Meta:
        unique_together = ("user", "conference", "role")

    def __str__(self):
        return f"{self.user} - {self.role} - {self.conference}"


class SubmissionChangeRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.submission.title} — {self.status}"


class ReviewAssignment(models.Model):
    ROLE_CHOICES = [
        ("judge", "Judge"),
        ("content_reviewer", "Content reviewer"),
        ("layout_reviewer", "Layout reviewer"),
    ]

    INVITATION_STATUS_CHOICES = [
        ("pending", "Invitation pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="review_assignments"
    )

    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="review_assignments"
    )

    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    assigned_at = models.DateTimeField(auto_now_add=True)

    invitation_status = models.CharField(
        max_length=20,
        choices=INVITATION_STATUS_CHOICES,
        default="pending",
        help_text="Reviewer invitation status for this assignment."
    )

    proposed_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline proposed by the judge when inviting the reviewer."
    )

    accepted_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Final deadline accepted or requested by the reviewer."
    )

    deadline_extension_requested = models.BooleanField(
        default=False,
        help_text="Reviewer requested a deadline different from the proposed one."
    )

    decline_reason = models.TextField(blank=True)
    review_invitation_sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)

    due_soon_reminder_sent = models.BooleanField(default=False)
    overdue_reminder_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ("submission", "reviewer", "role")

    def final_deadline(self):
        return self.accepted_deadline or self.proposed_deadline or self.submission.conference.review_deadline

    def __str__(self):
        return f"{self.submission.title} — {self.reviewer.username} — {self.role}"


class Review(models.Model):
    AUTHOR_SCALE_CHOICES = [
        ("yes", "Yes"),
        ("can_be_improved", "Can be improved"),
        ("must_be_improved", "Must be improved"),
        ("not_applicable", "Not applicable"),
    ]

    YES_NO_CHOICES = [
        ("yes", "Yes"),
        ("no", "No"),
    ]

    RATING_CHOICES = [
        ("high", "High"),
        ("average", "Average"),
        ("low", "Low"),
        ("no_answer", "No answer"),
    ]

    QUALITY_CHOICES = [
        ("poor", "Poor"),
        ("normal", "Normal"),
        ("good", "Good"),
        ("excellent", "Excellent"),
    ]

    PAPER_CLASSIFICATION_CHOICES = [
        ("review_paper", "Review paper"),
        ("research_paper", "Research paper"),
    ]

    ENGLISH_CHOICES = [
        ("needs_improvement", "The English could be improved."),
        ("fine", "The English is fine and does not require improvement."),
    ]

    RECOMMENDATION_CHOICES = [
        ("accept", "Accept in present form"),
        ("minor_revision", "Accept after minor revision"),
        ("major_revision", "Reconsider after major revision"),
        ("reject", "Reject"),
    ]

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    review_round = models.PositiveSmallIntegerField(
        default=0,
        help_text="Content review round for this review. Initial submission is round 0; author revisions use round 1, 2, etc."
    )

    content_context = models.CharField(
        max_length=30,
        choices=AUTHOR_SCALE_CHOICES,
        default="can_be_improved"
    )

    research_design = models.CharField(
        max_length=30,
        choices=AUTHOR_SCALE_CHOICES,
        default="can_be_improved"
    )

    arguments_discussion = models.CharField(
        max_length=30,
        choices=AUTHOR_SCALE_CHOICES,
        default="can_be_improved"
    )

    results_presented = models.CharField(
        max_length=30,
        choices=AUTHOR_SCALE_CHOICES,
        default="can_be_improved"
    )

    references_adequate = models.CharField(
        max_length=30,
        choices=AUTHOR_SCALE_CHOICES,
        default="can_be_improved"
    )

    conclusions_supported = models.CharField(
        max_length=30,
        choices=AUTHOR_SCALE_CHOICES,
        default="can_be_improved"
    )

    english_quality = models.CharField(
        max_length=30,
        choices=ENGLISH_CHOICES,
        default="fine"
    )

    comments_for_authors = models.TextField(blank=True)

    no_conflict_confirmed = models.BooleanField(
        default=False,
        help_text="Reviewer confirms there is no conflict of interest for this paper."
    )

    extension_requested = models.BooleanField(
        default=False,
        help_text="Reviewer requests an extension of the review deadline."
    )

    requested_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Requested new review deadline, if an extension is requested."
    )

    conflict_of_interest = models.CharField(
        max_length=10,
        choices=YES_NO_CHOICES,
        default="no"
    )

    plagiarism_detected = models.CharField(
        max_length=10,
        choices=YES_NO_CHOICES,
        default="no"
    )

    inappropriate_self_citations = models.CharField(
        max_length=10,
        choices=YES_NO_CHOICES,
        default="no"
    )

    ethical_concerns = models.CharField(
        max_length=10,
        choices=YES_NO_CHOICES,
        default="no"
    )

    originality = models.CharField(
        max_length=20,
        choices=RATING_CHOICES,
        default="average"
    )

    contribution = models.CharField(
        max_length=20,
        choices=RATING_CHOICES,
        default="average"
    )

    structure_clarity = models.CharField(
        max_length=20,
        choices=RATING_CHOICES,
        default="average"
    )

    logical_coherence = models.CharField(
        max_length=20,
        choices=RATING_CHOICES,
        default="average"
    )

    engagement_sources = models.CharField(
        max_length=20,
        choices=RATING_CHOICES,
        default="average"
    )

    overall_merit = models.CharField(
        max_length=20,
        choices=RATING_CHOICES,
        default="average"
    )

    references_relevant = models.CharField(
        max_length=10,
        choices=YES_NO_CHOICES,
        default="yes"
    )

    quality_originality = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        default="normal"
    )

    quality_scientific_contribution = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        default="normal"
    )

    quality_methodological_approach = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        default="normal"
    )

    quality_references = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        default="normal"
    )

    quality_clarity_expression = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        default="normal"
    )

    paper_classification = models.CharField(
        max_length=30,
        choices=PAPER_CLASSIFICATION_CHOICES,
        default="research_paper"
    )

    reviewer_competency = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        default="normal"
    )

    comments_for_editors = models.TextField(blank=True)

    overall_recommendation = models.CharField(
        max_length=30,
        choices=RECOMMENDATION_CHOICES,
        default="major_revision"
    )

    wants_final_notification = models.CharField(
        max_length=10,
        choices=YES_NO_CHOICES,
        default="no"
    )

    auto_score = models.FloatField(default=3.0)

    commented_paper_file = models.FileField(
        upload_to="reviewer_commented_papers/",
        storage=HybridDocumentStorage(),
        blank=True,
        null=True,
        help_text="Optional reviewer-uploaded paper with comments for the author.",
        max_length=500
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("submission", "reviewer", "review_round")

    def calculate_auto_score(self):
        """Calculate a 1-5 score from the current Green Building review form."""
        quality_map = {
            "poor": 1.5,
            "normal": 3.0,
            "good": 4.0,
            "excellent": 5.0,
        }

        fields = [
            self.quality_originality,
            self.quality_scientific_contribution,
            self.quality_methodological_approach,
            self.quality_references,
            self.quality_clarity_expression,
            self.reviewer_competency,
        ]

        values = [quality_map.get(value) for value in fields if quality_map.get(value) is not None]
        score = sum(values) / len(values) if values else 3.0

        recommendation_adjustments = {
            "accept": 0.4,
            "minor_revision": -0.1,
            "major_revision": -0.6,
            "reject": -1.5,
        }
        score += recommendation_adjustments.get(self.overall_recommendation, 0.0)

        if not self.no_conflict_confirmed:
            score -= 0.3
        if self.plagiarism_detected == "yes":
            score -= 1.0
        if self.ethical_concerns == "yes":
            score -= 1.0
        if self.conflict_of_interest == "yes":
            score -= 0.8

        return max(1.0, min(5.0, round(score, 1)))

    def save(self, *args, **kwargs):
        self.auto_score = self.calculate_auto_score()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.submission.title} — {self.reviewer.username}"


class EmailTemplate(models.Model):
    EVENT_CHOICES = [
        ("committee_login_info", "1. Scientific Committee login information"),
        ("reviewer_topics_request", "Reviewer topic selection request"),
        ("paper_submitted", "2. Submission confirmation – author"),
        ("coauthor_submission_confirmation", "3. Submission confirmation – co-author"),
        ("review_invitation", "4. Invitation to review manuscript"),
        ("review_request_accepted", "5. Review request accepted"),
        ("review_initiated", "6. Review initiated – author notification"),
        ("review_due_soon", "7. Reminder: review due soon"),
        ("review_overdue", "8. Reminder: review overdue"),
        ("review_received", "9. Confirmation of review receipt"),
        ("rereview_invitation", "10. Invitation to re-evaluate revised manuscript"),
        ("reviewer_editor_decision", "11. Reviewer notification of editor decision"),
        ("review_completed_author", "12. Review completed – author decision"),
        ("manuscript_accepted", "13. Manuscript accepted for publication"),
        ("layout_correction_needed", "14. Layout correction needed"),
        ("layout_correction_submitted", "15. Author correction submitted"),
        # Legacy/internal workflow events kept for existing code paths.
        ("reviewer_assigned", "Legacy: reviewer assigned"),
        ("revision_requested", "Legacy: content revision requested"),
        ("revision_uploaded", "Legacy: content revision uploaded"),
        ("accepted_for_layout", "Legacy: accepted for layout review"),
        ("layout_revision_requested", "Legacy: layout corrections requested"),
        ("layout_revision_uploaded", "Legacy: layout corrected paper uploaded"),
        ("final_accepted", "Legacy: final accepted"),
        ("rejected", "Legacy: rejected"),
    ]

    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    event = models.CharField(max_length=80, choices=EVENT_CHOICES)

    enabled = models.BooleanField(default=True)

    send_to_author = models.BooleanField(default=True)
    send_to_coauthors = models.BooleanField(default=True)
    send_to_reviewer = models.BooleanField(default=False)
    send_to_managers = models.BooleanField(default=False)
    send_to_layout_reviewers = models.BooleanField(default=False)

    subject = models.CharField(max_length=255)
    body = models.TextField()

    class Meta:
        ordering = ["event"]

    def __str__(self):
        return f"{self.conference.title_en} — {self.get_event_display()}"


class EmailLog(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("skipped", "Skipped"),
        ("failed", "Failed"),
    ]

    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, null=True, blank=True)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    event = models.CharField(max_length=80)
    recipient = models.EmailField(blank=True)
    subject = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event} — {self.recipient} — {self.status}"


class ConferenceInfoCard(models.Model):
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name="info_cards"
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    icon_image = models.ImageField(
        upload_to="conference_info_icons/",
        blank=True,
        null=True,
        help_text="Optional small image/icon shown next to the card title."
    )

    file = models.FileField(
        upload_to="conference_files/",
        storage=HybridDocumentStorage(),
        blank=True,
        null=True,
        max_length=500

    )

    order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.conference.title_en} - {self.title}"

    class Meta:
        ordering = ["order"]

class ConferenceSidebarCard(models.Model):
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name="sidebar_cards"
    )

    eyebrow = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    icon_image = models.ImageField(
        upload_to="conference_sidebar_icons/",
        blank=True,
        null=True,
        help_text="Optional small image/icon shown next to the sidebar card title."
    )

    order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.conference.title_en} - {self.title}"

    class Meta:
        ordering = ["order"]


class ConferenceFooterPartner(models.Model):
    PARTNER_TYPE_CHOICES = [
        ("organizer", "Organizer"),
        ("coorganizer", "Co-organizer"),
    ]

    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name="footer_partners"
    )

    partner_type = models.CharField(
        max_length=20,
        choices=PARTNER_TYPE_CHOICES,
        default="organizer"
    )

    name = models.CharField(max_length=200)

    logo = models.ImageField(
        upload_to="conference_footer_partners/",
        blank=True,
        null=True
    )

    website = models.URLField(blank=True)

    order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.conference.title_en} - {self.name}"

