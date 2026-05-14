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
        ("Dr.", "Dr."),
        ("Mr.", "Mr."),
        ("Mrs.", "Mrs."),
        ("Ms.", "Ms."),
        ("Mx.", "Mx."),
        ("Prof.", "Prof."),
        ("Prof. Dr.", "Prof. Dr."),
        ("Doc. dr.", "Doc. dr."),
        ("MA", "MA"),
        ("MS", "MS"),
        ("MSc", "MSc"),
        ("PhD", "PhD"),
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

    class Meta:
        model = Submission
        fields = [
            "title",
            "abstract",
            "keywords",
            "article_type",
            "first_author",
            "coauthors",
            "coauthor_emails",
            "topic",
            "secondary_topic",
            "full_paper_file",
        ]

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
        labels = {
            "title": "Paper title",
            "abstract": "Abstract",
            "keywords": "Keywords",
            "first_author": "First author (First Name Last Name)",
            "coauthors": "Co-authors (First Name Last Name)",
            "coauthor_emails": "Co-author email addresses",
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
        self.fields["article_type"].required = True
        self.fields["full_paper_file"].required = True
        self.fields["first_author"].required = True


class ReviewForm(forms.ModelForm):

    class Meta:
        model = Review
        fields = [
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
        ]

        widgets = {
            "quality_originality": forms.RadioSelect,
            "quality_scientific_contribution": forms.RadioSelect,
            "quality_methodological_approach": forms.RadioSelect,
            "quality_references": forms.RadioSelect,
            "quality_clarity_expression": forms.RadioSelect,
            "paper_classification": forms.RadioSelect,
            "reviewer_competency": forms.RadioSelect,
            "overall_recommendation": forms.RadioSelect,
            "comments_for_authors": forms.Textarea(attrs={"rows": 8}),
            "comments_for_editors": forms.Textarea(attrs={"rows": 7}),
        }

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
            "event",
            "enabled",
            "subject",
            "body",
        ]

        widgets = {
            "body": forms.Textarea(attrs={"rows": 14}),
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
