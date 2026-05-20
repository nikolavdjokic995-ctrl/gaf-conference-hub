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


MAX_ABSTRACT_WORDS = 300
MAX_PAPER_UPLOAD_MB = 50
MAX_PAPER_UPLOAD_BYTES = MAX_PAPER_UPLOAD_MB * 1024 * 1024
ALLOWED_PAPER_EXTENSIONS = [".doc", ".docx"]


TITLE_CHOICES = [
    ("", "Select"),
    ("Prof. Dr.", "Prof. Dr."),
    ("Assoc. Prof. Dr.", "Assoc. Prof. Dr."),
    ("Asst. Prof. Dr.", "Asst. Prof. Dr."),
    ("Dr.", "Dr."),
    ("Mr.", "Mr."),
    ("Ms.", "Ms."),
]


class RegisterForm(UserCreationForm):

    title = forms.ChoiceField(choices=TITLE_CHOICES)

    country = CountryField().formfield(
        widget=CountrySelectWidget()
    )

    privacy_consent = forms.BooleanField(
        required=True,
        label="I agree to the Privacy Policy and Terms of Use."
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
            "privacy_consent",
            "password1",
            "password2",
        ]


class SubmissionForm(forms.ModelForm):

    TITLE_CHOICES = [
        ("", "Select"),
        ("Prof. Dr.", "Prof. Dr."),
        ("Assoc. Prof. Dr.", "Assoc. Prof. Dr."),
        ("Asst. Prof. Dr.", "Asst. Prof. Dr."),
        ("Dr.", "Dr."),
        ("Mr.", "Mr."),
        ("Ms.", "Ms."),
    ]

    first_author_title = forms.ChoiceField(
        choices=TITLE_CHOICES,
        required=True,
        label="Title"
    )

    first_author_country = CountryField(blank_label="Select country").formfield(
        required=True,
        widget=CountrySelectWidget()
    )

    coauthor_titles = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Enter co-author titles, one per line, in the same order as co-authors.",
        })
    )

    coauthor_countries = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Enter co-author countries, one per line, in the same order as co-authors.",
        })
    )

    coauthor_affiliations = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Enter co-author affiliations, one per line, in the same order as co-authors.",
        })
    )

    coauthor_orcids = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Enter co-author ORCID iDs, one per line, in the same order as co-authors.",
        })
    )

    coauthors_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    submission_consent = forms.BooleanField(
        required=True,
        label="I confirm that the submission information is accurate and that I have permission to submit this manuscript on behalf of all listed authors."
    )

    class Meta:
        model = Submission
        fields = [
            "title",
            "abstract",
            "keywords",
            "article_type",
            "first_author_title",
            "first_author",
            "first_author_email",
            "first_author_country",
            "first_author_affiliation",
            "first_author_orcid",
            "coauthors",
            "coauthor_titles",
            "coauthor_emails",
            "coauthor_countries",
            "coauthor_affiliations",
            "coauthor_orcids",
            "topic",
            "secondary_topic",
            "full_paper_file",
            "coauthors_json",
            "submission_consent",
        ]

        labels = {
            "title": "Paper title",
            "abstract": "Abstract",
            "keywords": "Keywords",
            "article_type": "Article type",
            "first_author_title": "First author title",
            "first_author": "First author (First Name Last Name)",
            "first_author_email": "First author email",
            "first_author_country": "First author country",
            "first_author_affiliation": "First author affiliation",
            "first_author_orcid": "First author ORCID iD",
            "coauthors": "Co-authors (First Name Last Name)",
            "coauthor_titles": "Co-author titles",
            "coauthor_emails": "Co-author email addresses",
            "coauthor_countries": "Co-author countries",
            "coauthor_affiliations": "Co-author affiliations",
            "coauthor_orcids": "Co-author ORCID iDs",
            "topic": "Primary conference topic",
            "secondary_topic": "Second conference topic (optional)",
            "full_paper_file": "Full paper file",
        }

        widgets = {
            "abstract": forms.Textarea(attrs={
                "rows": 8,
                "placeholder": "Write your abstract here (maximum 300 words).",
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
            "first_author_affiliation": forms.TextInput(attrs={
                "placeholder": "Institution / university / organization",
            }),
            "first_author_orcid": forms.TextInput(attrs={
                "placeholder": "0000-0000-0000-0000",
            }),
        }


    def clean_coauthors_json(self):
        import json

        raw = self.cleaned_data.get("coauthors_json", "[]") or "[]"

        try:
            data = json.loads(raw)
        except Exception:
            raise forms.ValidationError("Invalid co-author data.")

        valid = []

        for item in data:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip()
            name = str(item.get("name", "")).strip()
            email = str(item.get("email", "")).strip()
            country = str(item.get("country", "")).strip()
            affiliation = str(item.get("affiliation", "")).strip()
            orcid = str(item.get("orcid", "")).strip()

            if title or name or email or country or affiliation or orcid:
                valid.append({
                    "title": title,
                    "name": name,
                    "email": email,
                    "country": country,
                    "affiliation": affiliation,
                    "orcid": orcid,
                })

        self.cleaned_data["parsed_coauthors"] = valid
        return raw


    def clean(self):
        cleaned_data = super().clean()
        raw_coauthors = cleaned_data.get("coauthors_json", "[]") or "[]"

        parsed = cleaned_data.get("parsed_coauthors")

        if parsed is None:
            import json

            try:
                data = json.loads(raw_coauthors)
            except Exception:
                data = []

            parsed = []

            for item in data:
                if not isinstance(item, dict):
                    continue

                title = str(item.get("title", "")).strip()
                name = str(item.get("name", "")).strip()
                email = str(item.get("email", "")).strip()
                country = str(item.get("country", "")).strip()
                affiliation = str(item.get("affiliation", "")).strip()
                orcid = str(item.get("orcid", "")).strip()

                if title or name or email or country or affiliation or orcid:
                    parsed.append({
                        "title": title,
                        "name": name,
                        "email": email,
                        "country": country,
                        "affiliation": affiliation,
                        "orcid": orcid,
                    })

        cleaned_data["parsed_coauthors"] = parsed

        # Populate legacy fields too. The Submission model and older templates
        # still read these text fields in dashboards and email workflows.
        cleaned_data["coauthors"] = "\n".join(
            item.get("name", "").strip()
            for item in parsed
            if item.get("name", "").strip()
        )
        cleaned_data["coauthor_titles"] = "\n".join(
            item.get("title", "").strip()
            for item in parsed
            if item.get("title", "").strip()
        )
        cleaned_data["coauthor_emails"] = "\n".join(
            item.get("email", "").strip()
            for item in parsed
            if item.get("email", "").strip()
        )
        cleaned_data["coauthor_countries"] = "\n".join(
            item.get("country", "").strip()
            for item in parsed
            if item.get("country", "").strip()
        )
        cleaned_data["coauthor_affiliations"] = "\n".join(
            item.get("affiliation", "").strip()
            for item in parsed
            if item.get("affiliation", "").strip()
        )
        cleaned_data["coauthor_orcids"] = "\n".join(
            item.get("orcid", "").strip()
            for item in parsed
            if item.get("orcid", "").strip()
        )

        return cleaned_data


    def clean_abstract(self):
        abstract = self.cleaned_data.get("abstract", "")
        words = [word for word in abstract.split() if word.strip()]

        if len(words) > MAX_ABSTRACT_WORDS:
            raise forms.ValidationError(
                f"The abstract must be no longer than {MAX_ABSTRACT_WORDS} words. Current length: {len(words)} words."
            )

        return abstract

    def clean_full_paper_file(self):
        file = self.cleaned_data.get("full_paper_file")

        if file:
            file_name = file.name.lower()

            if not any(file_name.endswith(ext) for ext in ALLOWED_PAPER_EXTENSIONS):
                raise forms.ValidationError(
                    "Please upload your paper in Word format only (.doc or .docx). PDF files are not accepted for paper submission."
                )

            if file.size > MAX_PAPER_UPLOAD_BYTES:
                raise forms.ValidationError(
                    f"The paper file must be smaller than {MAX_PAPER_UPLOAD_MB} MB. Please compress the file and try again."
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
        self.fields["first_author_title"].required = True
        self.fields["first_author_title"].required = False
        self.fields["first_author"].required = True
        self.fields["first_author_email"].required = True
        self.fields["first_author_country"].required = True
        self.fields["first_author_affiliation"].required = True
        self.fields["first_author_orcid"].required = False

        self.fields["coauthors"].required = False
        self.fields["coauthor_titles"].required = False
        self.fields["coauthor_emails"].required = False
        self.fields["coauthor_countries"].required = False
        self.fields["coauthor_affiliations"].required = False
        self.fields["coauthor_orcids"].required = False
        self.fields["coauthors_json"].required = False

        self.fields["full_paper_file"].widget.attrs.update({
            "accept": ".doc,.docx",
        })
        self.fields["abstract"].help_text = "Maximum 300 words."
        self.fields["full_paper_file"].help_text = "Accepted formats: DOC/DOCX only. Maximum file size: 50 MB."

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

class ReviewInvitationResponseForm(forms.Form):

    RESPONSE_CHOICES = [
        ("accept", "Accept review"),
        ("decline", "Decline review"),
    ]

    DEADLINE_CHOICES = [
        ("proposed", "I accept the proposed deadline"),
        ("different", "I request a different deadline"),
    ]

    response = forms.ChoiceField(
        choices=RESPONSE_CHOICES,
        widget=forms.RadioSelect,
        initial="accept",
        label="Your response"
    )

    deadline_choice = forms.ChoiceField(
        choices=DEADLINE_CHOICES,
        widget=forms.RadioSelect,
        initial="proposed",
        required=False,
        label="Review deadline"
    )

    requested_deadline = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Requested deadline"
    )

    decline_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Reason for declining (optional)"
    )

    def clean(self):
        cleaned_data = super().clean()
        response = cleaned_data.get("response")
        deadline_choice = cleaned_data.get("deadline_choice")
        requested_deadline = cleaned_data.get("requested_deadline")

        if response == "accept" and deadline_choice == "different" and not requested_deadline:
            self.add_error("requested_deadline", "Please select the deadline you would like to request.")

        return cleaned_data

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
            "overview_page_background_color",
            "overview_hero_background_color",
            "overview_section_background_color",
            "overview_card_background_color",
            "overview_hero_image_height",
            "overview_hero_buttons_margin_top",
            "overview_menu_width",
            "overview_menu_background",
            "overview_content_width",
            "overview_hero_height",
            "overview_card_background",
            "overview_text_color",
            "overview_section_background",
            "overview_secondary_background",
        ]

        widgets = {
            "title_en": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Green Building\nInternational Scientific Conference\n2026",
            }),
            "overview_page_background_color": forms.TextInput(attrs={"type": "color"}),
            "overview_hero_background_color": forms.TextInput(attrs={"type": "color"}),
            "overview_section_background_color": forms.TextInput(attrs={"type": "color"}),
            "overview_card_background_color": forms.TextInput(attrs={"type": "color"}),
            "overview_menu_background": forms.TextInput(attrs={"type": "color"}),
            "overview_card_background": forms.TextInput(attrs={"type": "color"}),
            "overview_text_color": forms.TextInput(attrs={"type": "color"}),
            "overview_section_background": forms.TextInput(attrs={"type": "color"}),
            "overview_secondary_background": forms.TextInput(attrs={"type": "color"}),
            "overview_hero_image_height": forms.NumberInput(attrs={"min": 250, "max": 1200, "step": 10}),
            "overview_hero_height": forms.NumberInput(attrs={"min": 250, "max": 1200, "step": 10}),
            "overview_menu_width": forms.NumberInput(attrs={"min": 160, "max": 520, "step": 10}),
            "overview_content_width": forms.NumberInput(attrs={"min": 600, "max": 1600, "step": 10}),
        }

        labels = {
            "overview_page_background_color": "Page background colour",
            "overview_hero_background_color": "Hero background colour",
            "overview_section_background_color": "Main section background colour",
            "overview_card_background_color": "Information card background colour",
            "overview_hero_image_height": "Hero image height",
            "overview_hero_buttons_margin_top": "Hero buttons margin top",
            "overview_menu_width": "Left menu width",
            "overview_menu_background": "Left menu background colour",
            "overview_content_width": "Main content width",
            "overview_hero_height": "Hero image block height",
            "overview_card_background": "Card background colour",
            "overview_text_color": "Main title/text colour",
            "overview_section_background": "Section background colour",
            "overview_secondary_background": "Secondary section background colour",
        }


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
        label="Upload revised full paper file",
        help_text="Accepted formats: DOC/DOCX only. Maximum file size: 50 MB."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_paper_file"].widget.attrs.update({
            "accept": ".doc,.docx",
        })

    def clean_full_paper_file(self):
        file = self.cleaned_data.get("full_paper_file")

        if file:
            file_name = file.name.lower()
            if not any(file_name.endswith(ext) for ext in ALLOWED_PAPER_EXTENSIONS):
                raise forms.ValidationError(
                    "Please upload the revised paper in Word format only (.doc or .docx). PDF files are not accepted."
                )

            if file.size > MAX_PAPER_UPLOAD_BYTES:
                raise forms.ValidationError(
                    f"The revised paper file must be smaller than {MAX_PAPER_UPLOAD_MB} MB."
                )

        return file


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

