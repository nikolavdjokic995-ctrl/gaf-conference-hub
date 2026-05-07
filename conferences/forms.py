from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    Submission,
    Review,
    Conference,
    ConferenceInfoCard,
    ConferenceTopic,
)


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    affiliation = forms.CharField(max_length=255)

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "affiliation",
            "password1",
            "password2",
        ]


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = [
            "title",
            "first_author",
            "coauthors",
            "topic",
            "full_paper_file",
        ]

        labels = {
            "title": "Paper title",
            "first_author": "First author",
            "coauthors": "Co-authors",
            "topic": "Conference topic",
            "full_paper_file": "Full paper file",
        }

        widgets = {
            "coauthors": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Enter co-authors, one per line",
            })
        }

    def __init__(self, *args, **kwargs):
        conference = kwargs.pop("conference", None)
        super().__init__(*args, **kwargs)

        if conference:
            self.fields["topic"].queryset = conference.topics.filter(
                enabled=True
            ).order_by("order", "code")
        else:
            self.fields["topic"].queryset = ConferenceTopic.objects.none()

        self.fields["topic"].empty_label = "Select conference topic"
        self.fields["topic"].required = True
        self.fields["full_paper_file"].required = True
        self.fields["first_author"].required = True


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = [
            "content_context",
            "research_design",
            "arguments_discussion",
            "results_presented",
            "references_adequate",
            "conclusions_supported",
            "english_quality",
            "comments_for_authors",
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
            "comments_for_editors",
            "overall_recommendation",
            "wants_final_notification",
        ]

        widgets = {
            "content_context": forms.RadioSelect,
            "research_design": forms.RadioSelect,
            "arguments_discussion": forms.RadioSelect,
            "results_presented": forms.RadioSelect,
            "references_adequate": forms.RadioSelect,
            "conclusions_supported": forms.RadioSelect,
            "english_quality": forms.RadioSelect,
            "conflict_of_interest": forms.RadioSelect,
            "plagiarism_detected": forms.RadioSelect,
            "inappropriate_self_citations": forms.RadioSelect,
            "ethical_concerns": forms.RadioSelect,
            "originality": forms.RadioSelect,
            "contribution": forms.RadioSelect,
            "structure_clarity": forms.RadioSelect,
            "logical_coherence": forms.RadioSelect,
            "engagement_sources": forms.RadioSelect,
            "overall_merit": forms.RadioSelect,
            "references_relevant": forms.RadioSelect,
            "overall_recommendation": forms.RadioSelect,
            "wants_final_notification": forms.RadioSelect,
            "comments_for_authors": forms.Textarea(attrs={"rows": 6}),
            "comments_for_editors": forms.Textarea(attrs={"rows": 6}),
        }


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
        fields = ["title", "description", "file", "order", "enabled"]


class ConferenceTopicForm(forms.ModelForm):
    class Meta:
        model = ConferenceTopic
        fields = ["code", "title", "description", "order", "enabled"]