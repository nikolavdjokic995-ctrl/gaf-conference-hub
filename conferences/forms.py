from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

from .models import (
    Submission,
    Review,
    Conference,
    ConferenceInfoCard,
    ConferenceSidebarCard,
    ConferenceTopic,
    EmailTemplate,
    ConferenceFooterPartner,
)


class RegisterForm(UserCreationForm):

    TITLE_CHOICES = [
        ("", "Select"),
        ("Prof. Dr.", "Prof. Dr."),
        ("Assoc. Prof. Dr.", "Assoc. Prof. Dr."),
        ("Asst. Prof. Dr.", "Asst. Prof. Dr."),
        ("Dr.", "Dr."),
        ("Mr.", "Mr."),
        ("Ms.", "Ms."),
    ]

    title = forms.ChoiceField(choices=TITLE_CHOICES)

    country = CountryField().formfield(
        widget=CountrySelectWidget()
    )

    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    affiliation = forms.CharField(max_length=255)

    class Meta:
        model = User
        fields = [
            "username",
            "title",
            "first_name",
            "last_name",
            "email",
            "affiliation",
            "country",
            "password1",
            "password2",
        ]


class SubmissionForm(forms.ModelForm):

    first_author_country = CountryField(blank_label="Select country").formfield(
        required=True,
        widget=CountrySelectWidget()
    )

    coauthor_countries = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Enter co-author countries, one per line, in the same order as co-authors.",
        })
    )

    class Meta:
        model = Submission
        fields = [
            "title",
            "abstract",
            "keywords",
            "article_type",
            "first_author",
            "first_author_email",
            "first_author_country",
            "coauthors",
            "coauthor_emails",
            "coauthor_countries",
            "topic",
            "secondary_topic",
            "full_paper_file",
        ]

        labels = {
            "title": "Paper title",
            "abstract": "Abstract",
            "keywords": "Keywords",
            "article_type": "Article type",
            "first_author": "First author (First Name Last Name)",
            "first_author_email": "First author email",
            "first_author_country": "First author country",
            "coauthors": "Co-authors (First Name Last Name)",
            "coauthor_emails": "Co-author email addresses",
            "coauthor_countries": "Co-author countries",
            "topic": "Primary conference topic",
            "secondary_topic": "Second conference topic (optional)",
            "full_paper_file": "Full paper file",
        }

        widgets = {
            "abstract": forms.Textarea(attrs={
                "rows": 8,
                "maxlength": 2500,
                "placeholder": "Write your abstract here (maximum 2500 characters).",
            }),
            "keywords": forms.TextInput(attrs={
                "placeholder": "e.g. green building, energy efficiency, sustainability",
            }),
            "coauthors": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Enter co-authors, one per line",
            }),
            "coauthor_emails": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Enter co-author emails, one per line",
            }),
        }

    def clean_full_paper_file(self):
        file = self.cleaned_data.get("full_paper_file")

        if file:
            allowed_extensions = [".doc", ".docx"]
            file_name = file.name.lower()

            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError(
                    "Please upload your paper in Word format only (.doc or .docx)."
                )

        return file

    def __init__(self, *args, **kwargs):
        conference = kwargs.pop("conference", None)
        super().__init__(*args, **kwargs)

        if conference:
            topics = conference.topics.filter(enabled=True).order_by("order", "code")
            self.fields["topic"].queryset = topics
            self.fields["secondary_topic"].queryset = topics
        else:
            self.fields["topic"].queryset = ConferenceTopic.objects.none()
            self.fields["secondary_topic"].queryset = ConferenceTopic.objects.none()

        self.fields["topic"].empty_label = "Select primary topic"
        self.fields["topic"].required = True
        self.fields["secondary_topic"].empty_label = "Select second topic if needed"
        self.fields["secondary_topic"].required = False
        self.fields["abstract"].required = True
        self.fields["keywords"].required = True
        self.fields["full_paper_file"].required = True
        self.fields["first_author"].required = True
        self.fields["first_author_email"].required = True
        self.fields["first_author_country"].required = True

class ReviewForm(forms.ModelForm):

    class Meta:
        model = Review
        fields = [
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
            "commented_paper_file",
            "comments_for_editors",
            "overall_recommendation",
            "wants_final_notification",
        ]

        widgets = {
            "requested_deadline": forms.DateInput(attrs={"type": "date"}),
            "quality_originality": forms.RadioSelect,
            "quality_scientific_contribution": forms.RadioSelect,
            "quality_methodological_approach": forms.RadioSelect,
            "quality_references": forms.RadioSelect,
            "quality_clarity_expression": forms.RadioSelect,
            "paper_classification": forms.RadioSelect,
            "reviewer_competency": forms.RadioSelect,
            "overall_recommendation": forms.RadioSelect,
            "wants_final_notification": forms.RadioSelect,
            "comments_for_authors": forms.Textarea(attrs={"rows": 8}),
            "comments_for_editors": forms.Textarea(attrs={"rows": 6}),
        }

        labels = {
            "no_conflict_confirmed": "I confirm that I have no conflict of interest for this paper.",
            "extension_requested": "Request review deadline extension",
            "requested_deadline": "Requested new deadline",
            "quality_originality": "Originality of the topic",
            "quality_scientific_contribution": "Scientific contribution",
            "quality_methodological_approach": "Methodological approach",
            "quality_references": "Quality of references",
            "quality_clarity_expression": "Clarity in expression",
            "paper_classification": "You would categorize this paper as",
            "reviewer_competency": "Reviewer competency in relation to the paper topic",
            "comments_for_authors": "Comments to the authors",
            "comments_for_editors": "Comments to the Editor (optional)",
            "commented_paper_file": "Review file",
            "overall_recommendation": "Overall recommendation",
            "wants_final_notification": "Would you like to be notified about the final decision?",
        }

    def clean(self):
        cleaned_data = super().clean()
        extension_requested = cleaned_data.get("extension_requested")
        requested_deadline = cleaned_data.get("requested_deadline")

        if extension_requested and not requested_deadline:
            self.add_error("requested_deadline", "Please select a requested deadline.")

        if not cleaned_data.get("no_conflict_confirmed"):
            self.add_error("no_conflict_confirmed", "You must confirm that you have no conflict of interest before submitting the review.")

        return cleaned_data

    def clean_commented_paper_file(self):
        file = self.cleaned_data.get("commented_paper_file")

        if file:
            allowed_extensions = [".doc", ".docx", ".pdf"]
            file_name = file.name.lower()

            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError(
                    "Please upload reviewer comments as .doc, .docx, or .pdf."
                )

        return file
class ConferenceForm(forms.ModelForm):

    class Meta:
        model = Conference
        fields = [
            "title_en",
            "title_sr",
            "slug",
            "description_en",
            "description_sr",
            "location",
            "start_date",
            "end_date",
            "submission_deadline",
            "review_deadline",
            "submission_mode",
            "logo",
            "hero_image",
            "template_style",
        ]


class ConferenceOverviewForm(forms.ModelForm):

    class Meta:
        model = Conference
        fields = [
            "title_en",
            "description_en",
            "location",
            "start_date",
            "end_date",
            "submission_deadline",
            "review_deadline",
            "organizer",
            "contact_email",
            "registration_url",
            "logo",
            "template_style",
            "hero_image",
            "overview_section_padding",
            "overview_section_radius",
            "overview_grid_min_width",
            "overview_grid_gap",
            "overview_card_padding",
            "overview_card_radius",
            "overview_card_title_size",
            "overview_card_text_size",
            "overview_stats_card_padding",
            "overview_stats_card_radius",
            "overview_stats_number_size",
            "overview_stats_label_size",
            "overview_about_padding",
            "overview_about_radius",
            "overview_about_title_size",
            "overview_about_text_size",
        ]


class SubmissionSettingsForm(forms.ModelForm):

    class Meta:
        model = Conference
        fields = [
            "submission_mode",
            "submission_deadline",
            "review_deadline",
        ]


class ConferenceInfoCardForm(forms.ModelForm):

    class Meta:
        model = ConferenceInfoCard
        fields = [
            "title",
            "description",
            "icon_image",
            "file",
            "order",
            "enabled",
        ]


class ConferenceSidebarCardForm(forms.ModelForm):

    class Meta:
        model = ConferenceSidebarCard
        fields = [
            "eyebrow",
            "title",
            "description",
            "icon_image",
            "order",
            "enabled",
        ]


class ConferenceTopicForm(forms.ModelForm):

    class Meta:
        model = ConferenceTopic
        fields = [
            "code",
            "title",
            "description",
            "order",
            "enabled",
        ]


class EmailTemplateForm(forms.ModelForm):

    class Meta:
        model = EmailTemplate
        fields = [
            "enabled",
            "send_to_author",
            "send_to_coauthors",
            "send_to_reviewer",
            "send_to_managers",
            "send_to_layout_reviewers",
            "subject",
            "body",
        ]

        widgets = {
            "body": forms.Textarea(attrs={"rows": 18}),
        }


class JudgeDecisionForm(forms.Form):

    STATUS_CHOICES = [
        ("accepted_for_layout", "Accept for layout review"),
        ("revision_required", "Request author revision"),
        ("rejected", "Reject"),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        label="Decision"
    )

    comment = forms.CharField(
        label="Decision message / instructions for author",
        widget=forms.Textarea(attrs={
            "rows": 6,
            "placeholder": "Write the decision message or revision instructions for the author.",
        }),
        required=False,
    )


class RevisionUploadForm(forms.Form):

    full_paper_file = forms.FileField(
        label="Upload revised full paper file"
    )


class LayoutDecisionForm(forms.Form):

    STATUS_CHOICES = [
        ("final_accepted", "Final accept"),
        ("layout_revision_required", "Request technical corrections"),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        label="Layout decision"
    )

    comment = forms.CharField(
        label="Technical correction instructions / final note",
        widget=forms.Textarea(attrs={
            "rows": 6,
            "placeholder": "Write technical corrections for the author, or a final layout note.",
        }),
        required=False,
    )

    final_publication_file = forms.FileField(
        label="Upload final print-ready paper",
        required=False,
        help_text="Optional. Upload the final version prepared for publication/printing."
    )
class ConferenceFooterForm(forms.ModelForm):

    class Meta:
        model = Conference
        fields = [
            "footer_description",
            "footer_copyright",
            "footer_contact_email",
            "footer_address",
            "footer_logo",
        ]


class ConferenceFooterPartnerForm(forms.ModelForm):

    class Meta:
        model = ConferenceFooterPartner
        fields = [
            "partner_type",
            "name",
            "logo",
            "website",
            "order",
            "enabled",
        ]
