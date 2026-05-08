from django.db import models
from django.contrib.auth.models import User
from cloudinary_storage.storage import RawMediaCloudinaryStorage

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    affiliation = models.CharField(max_length=255)

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}"
        return full_name.strip() or self.user.username


class Conference(models.Model):
    SUBMISSION_MODE_CHOICES = [
        ("full", "Full paper only"),
        ("abstract", "Abstract first, then full paper"),
    ]

    title_en = models.CharField(max_length=255)
    title_sr = models.CharField(max_length=255)
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

    def __str__(self):
        return self.title_en


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
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("under_review", "Under review"),
        ("revision_required", "Revision required"),
        ("accepted", "Accepted"),
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

    coauthors = models.TextField(
        blank=True,
        help_text="Separate co-authors with commas or new lines."
    )

    title = models.CharField(max_length=255)
    abstract = models.TextField(blank=True)

    abstract_file = models.FileField(
        upload_to="abstracts/",
        blank=True,
        null=True
    )

    full_paper_file = models.FileField(
        upload_to="papers/",
        storage=RawMediaCloudinaryStorage(),
        blank=True,
        null=True
    )

    topic = models.ForeignKey(
        ConferenceTopic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="submitted",
    )

    final_comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    class Meta:
        unique_together = ("submission", "reviewer", "role")

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

    auto_score = models.PositiveSmallIntegerField(default=3)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("submission", "reviewer")

    def calculate_auto_score(self):
        score = 5

        author_fields = [
            self.content_context,
            self.research_design,
            self.arguments_discussion,
            self.results_presented,
            self.references_adequate,
            self.conclusions_supported,
        ]

        for value in author_fields:
            if value == "can_be_improved":
                score -= 0.4
            elif value == "must_be_improved":
                score -= 0.8

        if self.english_quality == "needs_improvement":
            score -= 0.5

        editor_flags = [
            self.conflict_of_interest,
            self.plagiarism_detected,
            self.inappropriate_self_citations,
            self.ethical_concerns,
        ]

        for value in editor_flags:
            if value == "yes":
                score -= 1

        rating_fields = [
            self.originality,
            self.contribution,
            self.structure_clarity,
            self.logical_coherence,
            self.engagement_sources,
            self.overall_merit,
        ]

        for value in rating_fields:
            if value == "average":
                score -= 0.4
            elif value == "low":
                score -= 0.8
            elif value == "no_answer":
                score -= 0.3

        if self.references_relevant == "no":
            score -= 0.5

        if self.overall_recommendation == "minor_revision":
            score -= 0.5
        elif self.overall_recommendation == "major_revision":
            score -= 1.2
        elif self.overall_recommendation == "reject":
            score -= 2

        return max(1, min(5, round(score)))

    def save(self, *args, **kwargs):
        self.auto_score = self.calculate_auto_score()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.submission.title} — {self.reviewer.username}"


class EmailTemplate(models.Model):
    EVENT_CHOICES = [
        ("abstract_submitted", "Abstract submitted"),
        ("abstract_accepted", "Abstract accepted"),
        ("paper_submitted", "Full paper submitted"),
        ("decision_made", "Final decision sent"),
    ]

    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    event = models.CharField(max_length=50, choices=EVENT_CHOICES)

    enabled = models.BooleanField(default=True)

    subject = models.CharField(max_length=255)
    body = models.TextField()

    def __str__(self):
        return f"{self.conference.title_en} — {self.event}"


class ConferenceInfoCard(models.Model):
    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name="info_cards"
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    file = models.FileField(
        upload_to="conference_files/",
        blank=True,
        null=True
    )

    order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.conference.title_en} - {self.title}"

    class Meta:
        ordering = ["order"]