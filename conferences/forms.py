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
    ConferenceTopic,
)


class RegisterForm(UserCreationForm):

    TITLE_CHOICES = [
        ("Mr.", "Mr."),
        ("Ms.", "Ms."),
        ("Mrs.", "Mrs."),
        ("Dr.", "Dr."),
        ("Prof.", "Prof."),
        ("Prof. Dr.", "Prof. Dr."),
        ("BSc", "BSc"),
        ("MSc", "MSc"),
        ("MBA", "MBA"),
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
            "first_author",
            "coauthors",
            "coauthor_emails",
            "topic",
            "secondary_topic",
            "full_paper_file",
        ]

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

            topics = conference.topics.filter(
                enabled=True
            ).order_by("order", "code")

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


class ReviewForm(forms.ModelForm):

    class Meta:
        model = Review

        fields = [
            "content_context",
            "research_design",
            "arguments_discussion",
            "overall_recommendation",
            "comments_for_authors",
            "comments_for_editors",
        ]

        widgets = {
            "comments_for_authors": forms.Textarea(attrs={"rows": 4}),
            "comments_for_editors": forms.Textarea(attrs={"rows": 4}),
        }


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
            "organizer",
            "contact_email",
            "registration_url",
            "logo",
            "template_style",
            "hero_image",
        ]

class ConferenceInfoCardForm(forms.ModelForm):

    class Meta:
        model = ConferenceInfoCard

        fields = [
            "title",
            "description",
            "file",
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
