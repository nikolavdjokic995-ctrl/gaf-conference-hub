
import os
import tempfile
import urllib.request
import cloudinary.uploader
from django.http import HttpResponse
from django.core.files import File
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.core.mail import send_mail
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from pathlib import Path
from datetime import datetime

from .models import (
    Conference,
    ConferenceRole,
    Submission,
    ReviewAssignment,
    Review,
    EmailTemplate,
    EmailLog,
    ConferenceInfoCard,
    ConferenceSidebarCard,
    ConferenceTopic,
    ConferenceFooterPartner,
    UserProfile,
)

from .forms import (
    ReviewForm,
    ConferenceOverviewForm,
    SubmissionForm,
    ConferenceInfoCardForm,
    ConferenceSidebarCardForm,
    ConferenceTopicForm,
    RegisterForm,
    JudgeDecisionForm,
    RevisionUploadForm,
    LayoutDecisionForm,
    EmailTemplateForm,
    SubmissionSettingsForm,
    ConferenceFooterForm,
    ConferenceFooterPartnerForm,
)

from .emails import send_event_email, preview_template, send_test_template_email, send_conference_role_email
from .email_defaults import OFFICIAL_EMAIL_EVENTS
from .email_automation import process_scheduled_review_emails, get_email_workflow_status
from .utils import anonymize_docx

@login_required
def send_test_email_template(request, template_id):
    template = get_object_or_404(EmailTemplate, id=template_id)
    conference = template.conference

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        recipient = request.POST.get("test_recipient", "").strip()
        ok, message = send_test_template_email(template, recipient, request=request)

        if ok:
            messages.success(request, message)
        else:
            messages.error(request, message)

    return redirect("email_templates", slug=conference.slug)

@login_required
def review_invitation_response(request, assignment_id):
    assignment = get_object_or_404(
        ReviewAssignment,
        id=assignment_id,
        reviewer=request.user
    )

    submission = assignment.submission
    conference = submission.conference

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "accept":
            deadline_choice = request.POST.get("deadline_choice")

            assignment.invitation_status = "accepted"
            assignment.accepted_at = timezone.now()

            if deadline_choice == "proposed":
                assignment.accepted_deadline = assignment.proposed_deadline
                assignment.deadline_extension_requested = False

            elif deadline_choice == "custom":
                requested_deadline = request.POST.get("requested_deadline")

                if not requested_deadline:
                    messages.error(
                        request,
                        "Please select the date by which you can complete the review."
                    )
                    return redirect(
                        "review_invitation_response",
                        assignment_id=assignment.id
                    )

                try:
                    parsed_date = datetime.strptime(
                        requested_deadline,
                        "%Y-%m-%d"
                    ).date()
                except ValueError:
                    messages.error(
                        request,
                        "Invalid requested deadline format."
                    )
                    return redirect(
                        "review_invitation_response",
                        assignment_id=assignment.id
                    )

                assignment.accepted_deadline = parsed_date
                assignment.deadline_extension_requested = True

            assignment.save()

            send_event_email(
                "review_request_accepted",
                submission,
                request=request,
                reviewer=assignment.reviewer,
                assignment=assignment,
            )

            messages.success(
                request,
                "Review invitation accepted successfully."
            )

            return redirect(
                "review_submission",
                submission_id=submission.id
            )

        if action == "decline":
            assignment.invitation_status = "declined"
            assignment.declined_at = timezone.now()
            assignment.decline_reason = request.POST.get("decline_reason", "")
            assignment.save()

            messages.success(
                request,
                "Review invitation declined."
            )

            return redirect("my_reviews")

    return render(
        request,
        "conferences/review_invitation_response.html",
        {
            "assignment": assignment,
            "submission": submission,
            "conference": conference,
        }
    )


def home(request):
    conferences = Conference.objects.all()

    is_manager = False
    is_judge = False
    is_reviewer = False
    is_layout_reviewer = False

    if request.user.is_authenticated:
        is_manager = ConferenceRole.objects.filter(
            user=request.user,
            role="manager"
        ).exists()

        is_judge = ConferenceRole.objects.filter(
            user=request.user,
            role="judge"
        ).exists()

        is_reviewer = ConferenceRole.objects.filter(
            user=request.user,
            role="content_reviewer"
        ).exists()

        is_layout_reviewer = ConferenceRole.objects.filter(
            user=request.user,
            role="layout_reviewer"
        ).exists()

    return render(request, "conferences/home.html", {
        "conferences": conferences,
        "is_manager": is_manager,
        "is_judge": is_judge,
        "is_reviewer": is_reviewer,
        "is_layout_reviewer": is_layout_reviewer,
    })


def conference_overview(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    submission_closed = (
        conference.submission_deadline
        and timezone.now().date() > conference.submission_deadline
    )

    can_submit = request.user.is_authenticated
    is_manager = False
    is_reviewer = False
    is_judge = False
    is_layout_reviewer = False

    if request.user.is_authenticated:
        is_manager = ConferenceRole.objects.filter(
            conference=conference,
            user=request.user,
            role="manager"
        ).exists()

        is_reviewer = ConferenceRole.objects.filter(
            conference=conference,
            user=request.user,
            role__in=["content_reviewer", "layout_reviewer"]
        ).exists()

        is_judge = ConferenceRole.objects.filter(
            conference=conference,
            user=request.user,
            role="judge"
        ).exists()

        is_layout_reviewer = ConferenceRole.objects.filter(
            conference=conference,
            user=request.user,
            role="layout_reviewer"
        ).exists()

    footer_partners = ConferenceFooterPartner.objects.filter(
        conference=conference,
        enabled=True
    ).order_by("order", "name")

    country_set = set()

    registered_countries = (
        UserProfile.objects
        .exclude(country__isnull=True)
        .exclude(country="")
        .values_list("country", flat=True)
        .distinct()
    )

    country_set.update(
        str(country).strip()
        for country in registered_countries
        if str(country).strip()
    )

    submission_country_rows = Submission.objects.filter(
        conference=conference
    ).values_list("first_author_country", "coauthor_countries")

    for first_author_country, coauthor_countries in submission_country_rows:
        if first_author_country and str(first_author_country).strip():
            country_set.add(str(first_author_country).strip())

        if coauthor_countries:
            for country in str(coauthor_countries).replace(";", "\n").replace(",", "\n").splitlines():
                country = country.strip()
                if country:
                    country_set.add(country)

    participating_countries = len(country_set)

    stats = {
        "submitted_papers": Submission.objects.filter(conference=conference).count(),
        "accepted_papers": Submission.objects.filter(
            conference=conference,
            status="final_accepted"
        ).count(),
        "participating_countries": participating_countries,
        "topics": ConferenceTopic.objects.filter(
            conference=conference,
            enabled=True
        ).count(),
    }

    return render(request, "conferences/conference_overview.html", {
        "conference": conference,
        "can_submit": can_submit,
        "is_manager": is_manager,
        "is_reviewer": is_reviewer,
        "is_judge": is_judge,
        "is_layout_reviewer": is_layout_reviewer,
        "submission_closed": submission_closed,
        "footer_partners": footer_partners,
        "stats": stats,
    })

@login_required
def make_decision(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    role = ConferenceRole.objects.filter(
        user=request.user,
        conference=submission.conference,
        role__in=["judge", "manager"]
    ).exists()

    if not role:
        return redirect("/")

    if request.method == "POST":
        form = JudgeDecisionForm(request.POST)

        if form.is_valid():
            status = form.cleaned_data["status"]
            comment = form.cleaned_data["comment"]

            submission.status = status
            submission.final_comment = comment

            if status == "revision_required":
                submission.judge_revision_message = comment
                submission.revision_round += 1

            submission.save()

            if status == "revision_required":
                send_event_email("revision_requested", submission, request=request)
            elif status == "accepted_for_layout":
                send_event_email("accepted_for_layout", submission, request=request)
            elif status == "rejected":
                send_event_email("rejected", submission, request=request)

            # Notify accepted reviewers that the final/editor decision has been made.
            # Template 11: Reviewer notification of editor decision.
            accepted_assignments = ReviewAssignment.objects.filter(
                submission=submission,
                role="content_reviewer",
                invitation_status="accepted",
            ).select_related("reviewer")

            for assignment in accepted_assignments:
                send_event_email(
                    "reviewer_notification_of_editor_decision",
                    submission,
                    request=request,
                    reviewer=assignment.reviewer,
                    assignment=assignment,
                )

            messages.success(request, "Decision saved successfully.")
            return redirect("submission_result", submission_id=submission.id)
    else:
        form = JudgeDecisionForm(initial={
            "status": submission.status if submission.status in ["accepted_for_layout", "revision_required", "rejected"] else "accepted_for_layout",
            "comment": submission.final_comment,
        })

    return render(request, "conferences/make_decision.html", {
        "submission": submission,
        "form": form,
    })


@login_required
def assign_papers(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    can_assign = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role__in=["manager", "judge"]
    ).exists()

    if not can_assign:
        return redirect("/")

    submissions = Submission.objects.filter(
        conference=conference
    ).select_related(
        "author",
        "topic",
        "secondary_topic"
    ).prefetch_related(
        "review_assignments__reviewer"
    )

    reviewers = ConferenceRole.objects.filter(
        conference=conference,
        role="content_reviewer"
    ).select_related("user").prefetch_related("topics")

    if request.method == "POST":
        submission_id = request.POST.get("submission_id")
        reviewer_role_id = request.POST.get("reviewer_role_id")
        proposed_deadline = request.POST.get("proposed_deadline")

        submission = get_object_or_404(
            Submission,
            id=submission_id,
            conference=conference
        )

        reviewer_role = get_object_or_404(
            ConferenceRole,
            id=reviewer_role_id,
            conference=conference
        )

        assignment, created = ReviewAssignment.objects.get_or_create(
            submission=submission,
            reviewer=reviewer_role.user,
            role=reviewer_role.role,
            defaults={
                "proposed_deadline": proposed_deadline or None
            }
        )

        if not created and proposed_deadline:
            assignment.proposed_deadline = proposed_deadline
            assignment.invitation_status = "pending"
            assignment.accepted_deadline = None
            assignment.deadline_extension_requested = False
            assignment.accepted_at = None
            assignment.declined_at = None
            assignment.decline_reason = ""
            assignment.save()

        if created:
            send_event_email(
                "review_invitation",
                submission,
                request=request,
                reviewer=reviewer_role.user,
            )

            send_event_email(
                "review_initiated",
                submission,
                request=request,
            )

        submission.status = "under_review"
        submission.save()

        return redirect("assign_papers", slug=conference.slug)

    submission_data = []

    for submission in submissions:
        topic_ids = [
            topic.id
            for topic in [submission.topic, submission.secondary_topic]
            if topic
        ]

        suggested_reviewers = reviewers.filter(
            topics__id__in=topic_ids
        ).distinct() if topic_ids else reviewers.none()

        submission_data.append({
            "submission": submission,
            "suggested_reviewers": suggested_reviewers,
            "all_reviewers": reviewers,
            "assignments": submission.review_assignments.all(),
        })

    return render(request, "conferences/assign_papers.html", {
        "conference": conference,
        "submission_data": submission_data,
    })

@login_required
def review_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    assigned = ReviewAssignment.objects.filter(
        submission=submission,
        reviewer=request.user,
        role="content_reviewer"
    ).exists()

    if not assigned:
        return redirect("/")

    current_round = submission.revision_round or 0

    existing_review = Review.objects.filter(
        submission=submission,
        reviewer=request.user,
        review_round=current_round
    ).first()

    if request.method == "POST":
        if existing_review:
            form = ReviewForm(request.POST, request.FILES, instance=existing_review)
        else:
            form = ReviewForm(request.POST, request.FILES)

        if form.is_valid():
            review = form.save(commit=False)
            review.submission = submission
            review.reviewer = request.user
            review.review_round = current_round
            review.save()

            messages.success(request, f"Review for round {current_round} saved successfully.")
            return redirect("/my-reviews/")
    else:
        form = ReviewForm(instance=existing_review)

    return render(request, "conferences/review_form.html", {
        "form": form,
        "submission": submission,
        "current_round": current_round,
        "existing_review": existing_review,
    })

@login_required
def submission_result(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    reviews = Review.objects.filter(submission=submission).select_related("reviewer").order_by("review_round", "reviewer__username")
    avg_score = reviews.aggregate(Avg("auto_score"))["auto_score__avg"]

    decision = submission.get_status_display()

    can_manage = ConferenceRole.objects.filter(
        user=request.user,
        conference=submission.conference,
        role__in=["judge", "manager"]
    ).exists()

    return render(request, "conferences/submission_result.html", {
        "submission": submission,
        "reviews": reviews,
        "avg_score": avg_score,
        "decision": decision,
        "can_manage": can_manage,
    })


@login_required
def send_revision_to_reviewers(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    can_manage = ConferenceRole.objects.filter(
        user=request.user,
        conference=submission.conference,
        role__in=["judge", "manager"]
    ).exists()

    if not can_manage:
        return redirect("/")

    if request.method != "POST":
        return redirect("submission_result", submission_id=submission.id)

    if submission.status != "revised_submitted":
        messages.error(request, "This submission does not have a revised paper waiting for content review.")
        return redirect("submission_result", submission_id=submission.id)

    reviewer_count = ReviewAssignment.objects.filter(
        submission=submission,
        role="content_reviewer"
    ).count()

    if reviewer_count == 0:
        messages.error(request, "No content reviewers are assigned to this submission. Assign reviewers first.")
        return redirect("submission_result", submission_id=submission.id)

    submission.status = "under_review"
    submission.save(update_fields=["status", "updated_at"])

    messages.success(
        request,
        f"Revised paper round {submission.revision_round} has been sent back to {reviewer_count} reviewer(s)."
    )
    return redirect("submission_result", submission_id=submission.id)


@login_required
def manager_dashboard(request):
    is_manager = ConferenceRole.objects.filter(
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    submissions = Submission.objects.all()
    data = []

    for submission in submissions:
        reviews = Review.objects.filter(submission=submission)
        avg = reviews.aggregate(Avg("auto_score"))["auto_score__avg"]

        data.append({
            "submission": submission,
            "avg": avg,
            "decision": submission.get_status_display(),
            "count": reviews.count()
        })

    return render(request, "conferences/dashboard.html", {
        "data": data
    })


@login_required
def judge_dashboard(request):
    selected_status = request.GET.get("status", "all")

    judge_roles = ConferenceRole.objects.filter(
        user=request.user,
        role__in=["judge", "manager"]
    )

    if not judge_roles.exists():
        return redirect("/")

    conferences = [role.conference for role in judge_roles]

    submissions = Submission.objects.filter(conference__in=conferences)

    if selected_status != "all":
        submissions = submissions.filter(status=selected_status)

    data = []

    for submission in submissions:
        reviews = Review.objects.filter(submission=submission)
        avg_auto_score = reviews.aggregate(Avg("auto_score"))["auto_score__avg"]
        data.append({
            "submission": submission,
            "reviews": reviews,
            "review_count": reviews.count(),
            "accept_count": reviews.filter(overall_recommendation="accept").count(),
            "minor_count": reviews.filter(overall_recommendation="minor_revision").count(),
            "major_count": reviews.filter(overall_recommendation="major_revision").count(),
            "reject_count": reviews.filter(overall_recommendation="reject").count(),
            "status": submission.status,
            "status_display": submission.get_status_display(),
            "avg_score": avg_auto_score,
        })

    return render(request, "conferences/judge_dashboard.html", {
        "data": data,
        "selected_status": selected_status,
    })

@login_required
def edit_conference_overview(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        form = ConferenceOverviewForm(
            request.POST,
            request.FILES,
            instance=conference
        )

        if form.is_valid():
            form.save()
            return redirect("conference_overview", slug=conference.slug)
    else:
        form = ConferenceOverviewForm(instance=conference)

    return render(request, "conferences/edit_conference_overview.html", {
        "form": form,
        "conference": conference,
    })


@login_required
def conference_settings(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    return render(request, "conferences/conference_settings.html", {
        "conference": conference
    })


@login_required
def edit_submission_settings(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        form = SubmissionSettingsForm(request.POST, instance=conference)

        if form.is_valid():
            form.save()
            messages.success(request, "Submission settings updated successfully.")
            return redirect("conference_settings", slug=conference.slug)
    else:
        form = SubmissionSettingsForm(instance=conference)

    return render(request, "conferences/edit_submission_settings.html", {
        "conference": conference,
        "form": form,
    })


@login_required
def email_templates(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    templates_qs = EmailTemplate.objects.filter(
        conference=conference,
        event__in=OFFICIAL_EMAIL_EVENTS,
    )
    templates_by_event = {template.event: template for template in templates_qs}
    templates = [templates_by_event[event] for event in OFFICIAL_EMAIL_EVENTS if event in templates_by_event]

    logs = EmailLog.objects.filter(
        conference=conference
    ).select_related("submission", "template")[:40]

    return render(request, "conferences/email_templates.html", {
        "conference": conference,
        "templates": templates,
        "logs": logs,
    })


@login_required
def edit_email_template(request, template_id):
    template = get_object_or_404(EmailTemplate, id=template_id)
    conference = template.conference

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        form = EmailTemplateForm(request.POST, instance=template)

        if form.is_valid():
            form.save()
            messages.success(request, "Email template saved successfully.")
            return redirect("email_templates", slug=conference.slug)
    else:
        form = EmailTemplateForm(instance=template)

    preview = preview_template(template, request=request)

    return render(request, "conferences/email_template_form.html", {
        "conference": conference,
        "template": template,
        "form": form,
        "preview": preview,
    })


@login_required
def preview_email_template(request, template_id):
    template = get_object_or_404(EmailTemplate, id=template_id)
    conference = template.conference

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    preview = preview_template(template, request=request)

    return render(request, "conferences/email_template_preview.html", {
        "conference": conference,
        "template": template,
        "preview": preview,
    })


@login_required
def submit_paper(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    if request.method == "POST":
        form = SubmissionForm(request.POST, request.FILES, conference=conference)

        if form.is_valid():
            try:
                submission = form.save(commit=False)
                submission.conference = conference
                submission.author = request.user
                submission.submitted_by = request.user
                submission.status = "submitted"

                # Generate unique paper code safely
                conference_code = conference.slug.replace("-", "").upper()[:6]

                last_submission = (
                    Submission.objects
                    .filter(conference=conference)
                    .exclude(paper_code="")
                    .order_by("-id")
                    .first()
                )

                next_number = 1

                if last_submission and last_submission.paper_code:
                    try:
                        next_number = int(
                            last_submission.paper_code.split("-")[-1]
                        ) + 1
                    except Exception:
                        next_number = (
                            Submission.objects.filter(
                                conference=conference
                            ).count() + 1
                        )

                while True:
                    generated_code = f"{conference_code}-{next_number:03d}"

                    if not Submission.objects.filter(
                        paper_code=generated_code
                    ).exists():
                        break

                    next_number += 1

                submission.paper_code = generated_code

                submission.save()

                uploaded_file = request.FILES.get("full_paper_file")

                if uploaded_file:
                    extension = os.path.splitext(uploaded_file.name)[1].lower()

                    source_path = None
                    anonymized_path = None

                    try:
                        # Save uploaded file temporarily
                        with tempfile.NamedTemporaryFile(
                            suffix=extension,
                            delete=False
                        ) as source_tmp:

                            for chunk in uploaded_file.chunks():
                                source_tmp.write(chunk)

                            source_path = source_tmp.name

                        # =========================
                        # SAVE ORIGINAL PAPER
                        # =========================

                        original_public_id = (
                            f"media/papers/originals/"
                            f"{submission.paper_code}_submission_{submission.id}"
                        )

                        cloudinary.uploader.upload(
                            source_path,
                            resource_type="raw",
                            public_id=original_public_id,
                            overwrite=True,
                            invalidate=True,
                            unique_filename=False,
                            use_filename=False,
                        )

                        submission.full_paper_file.name = (
                            f"{original_public_id}{extension}"
                        )

                        # Preserve the very first author-submitted version forever.
                        # Layout reviewers use this file to recover author metadata
                        # and original formatting during final publication preparation.
                        if not submission.original_submission_file:
                            submission.original_submission_file.name = (
                                f"{original_public_id}{extension}"
                            )

                        # =========================
                        # SAVE ANONYMIZED VERSION
                        # =========================

                        if extension == ".docx":

                            with tempfile.NamedTemporaryFile(
                                suffix=".docx",
                                delete=False
                            ) as anonymized_tmp:

                                anonymized_path = anonymized_tmp.name

                            anonymize_docx(source_path, anonymized_path)

                            if (
                                not anonymized_path
                                or not os.path.exists(anonymized_path)
                                or os.path.getsize(anonymized_path) == 0
                            ):
                                raise ValueError(
                                    "Anonymized DOCX was not created correctly."
                                )

                            anonymous_public_id = (
                                f"media/anonymous_papers/"
                                f"{submission.paper_code}_submission_{submission.id}"
                            )

                            cloudinary.uploader.upload(
                                anonymized_path,
                                resource_type="raw",
                                public_id=anonymous_public_id,
                                overwrite=True,
                                invalidate=True,
                                unique_filename=False,
                                use_filename=False,
                            )

                            submission.anonymized_paper_file.name = (
                                f"{anonymous_public_id}.docx"
                            )

                        submission.save()

                    finally:
                        if source_path and os.path.exists(source_path):
                            os.remove(source_path)

                        if anonymized_path and os.path.exists(anonymized_path):
                            os.remove(anonymized_path)

                send_event_email("paper_submitted", submission, request=request)
                send_event_email("coauthor_submission_confirmation", submission, request=request)

                messages.success(request, "Paper submitted successfully.")
                return redirect("my_submissions")

            except Exception as e:
                print("Paper upload/anonymization error:", e)
                messages.error(request, f"Paper upload failed: {e}")

        else:
            print("FORM ERRORS:", form.errors)
            messages.error(request, f"Form errors: {form.errors}")

    else:
        form = SubmissionForm(conference=conference)

    return render(
        request,
        "conferences/submit.html",
        {
            "conference": conference,
            "form": form,
        },
    )

@login_required
def important_information(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    cards = ConferenceInfoCard.objects.filter(
        conference=conference,
        enabled=True
    ).order_by("order")

    topics = ConferenceTopic.objects.filter(
        conference=conference,
        enabled=True
    ).order_by("order", "code")

    sidebar_cards = ConferenceSidebarCard.objects.filter(
        conference=conference,
        enabled=True
    ).order_by("order")

    is_manager = False
    if request.user.is_authenticated:
        is_manager = ConferenceRole.objects.filter(
            conference=conference,
            user=request.user,
            role="manager"
        ).exists()

    return render(request, "conferences/important_information.html", {
        "conference": conference,
        "cards": cards,
        "topics": topics,
        "sidebar_cards": sidebar_cards,
        "is_manager": is_manager,
    })

@login_required
def add_info_card(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        form = ConferenceInfoCardForm(request.POST, request.FILES)

        if form.is_valid():
            card = form.save(commit=False)
            card.conference = conference
            card.save()
            return redirect("important_information", slug=conference.slug)
    else:
        form = ConferenceInfoCardForm()

    return render(request, "conferences/info_card_form.html", {
        "form": form,
        "conference": conference,
    })

@login_required
def edit_info_card(request, card_id):
    card = get_object_or_404(ConferenceInfoCard, id=card_id)

    is_manager = ConferenceRole.objects.filter(
        conference=card.conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        form = ConferenceInfoCardForm(
            request.POST,
            request.FILES,
            instance=card
        )

        if form.is_valid():
            form.save()
            return redirect(
                "important_information",
                slug=card.conference.slug
            )
    else:
        form = ConferenceInfoCardForm(instance=card)

    return render(request, "conferences/info_card_form.html", {
        "form": form,
        "conference": card.conference,
    })


@login_required
def delete_info_card(request, card_id):
    card = get_object_or_404(ConferenceInfoCard, id=card_id)

    is_manager = ConferenceRole.objects.filter(
        conference=card.conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    conference_slug = card.conference.slug
    card.delete()

    return redirect(
        "important_information",
        slug=conference_slug
    )


@login_required
def add_sidebar_card(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        form = ConferenceSidebarCardForm(request.POST, request.FILES)

        if form.is_valid():
            sidebar_card = form.save(commit=False)
            sidebar_card.conference = conference
            sidebar_card.save()
            return redirect("important_information", slug=conference.slug)
    else:
        form = ConferenceSidebarCardForm()

    return render(request, "conferences/sidebar_card_form.html", {
        "form": form,
        "conference": conference,
    })


@login_required
def edit_sidebar_card(request, sidebar_card_id):
    sidebar_card = get_object_or_404(ConferenceSidebarCard, id=sidebar_card_id)

    is_manager = ConferenceRole.objects.filter(
        conference=sidebar_card.conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        form = ConferenceSidebarCardForm(
            request.POST,
            request.FILES,
            instance=sidebar_card
        )

        if form.is_valid():
            form.save()
            return redirect(
                "important_information",
                slug=sidebar_card.conference.slug
            )
    else:
        form = ConferenceSidebarCardForm(instance=sidebar_card)

    return render(request, "conferences/sidebar_card_form.html", {
        "form": form,
        "conference": sidebar_card.conference,
    })


@login_required
def delete_sidebar_card(request, sidebar_card_id):
    sidebar_card = get_object_or_404(ConferenceSidebarCard, id=sidebar_card_id)

    is_manager = ConferenceRole.objects.filter(
        conference=sidebar_card.conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    conference_slug = sidebar_card.conference.slug
    sidebar_card.delete()

    return redirect(
        "important_information",
        slug=conference_slug
    )


@login_required
def conference_topics(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = False

    if request.user.is_authenticated:
        is_manager = ConferenceRole.objects.filter(
            conference=conference,
            user=request.user,
            role="manager"
        ).exists()

    if is_manager:
        topics = ConferenceTopic.objects.filter(
            conference=conference
        ).order_by("order", "code")
    else:
        topics = ConferenceTopic.objects.filter(
            conference=conference,
            enabled=True
        ).order_by("order", "code")

    sidebar_cards = ConferenceSidebarCard.objects.filter(
        conference=conference,
        enabled=True
    ).order_by("order")

    return render(request, "conferences/conference_topics.html", {
        "conference": conference,
        "topics": topics,
        "sidebar_cards": sidebar_cards,
        "is_manager": is_manager,
    })

@login_required
def add_conference_topic(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        form = ConferenceTopicForm(request.POST)

        if form.is_valid():
            topic = form.save(commit=False)
            topic.conference = conference
            topic.save()
            return redirect("conference_topics", slug=conference.slug)
    else:
        form = ConferenceTopicForm()

    return render(request, "conferences/topic_form.html", {
        "form": form,
        "conference": conference,
    })


@login_required
def edit_conference_topic(request, topic_id):
    topic = get_object_or_404(ConferenceTopic, id=topic_id)

    is_manager = ConferenceRole.objects.filter(
        conference=topic.conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    if request.method == "POST":
        form = ConferenceTopicForm(request.POST, instance=topic)

        if form.is_valid():
            form.save()
            return redirect("conference_topics", slug=topic.conference.slug)
    else:
        form = ConferenceTopicForm(instance=topic)

    return render(request, "conferences/topic_form.html", {
        "form": form,
        "conference": topic.conference,
    })


@login_required
def delete_conference_topic(request, topic_id):
    topic = get_object_or_404(ConferenceTopic, id=topic_id)

    is_manager = ConferenceRole.objects.filter(
        conference=topic.conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    slug = topic.conference.slug
    topic.delete()

    return redirect("conference_topics", slug=slug)


@login_required
def my_submissions(request):
    submissions = Submission.objects.filter(
        author=request.user
    ).select_related("conference", "topic", "secondary_topic").order_by("-created_at")

    return render(request, "conferences/my_submissions.html", {
        "submissions": submissions
    })


@login_required
def conference_submissions(request, slug):

    conference = get_object_or_404(
        Conference,
        slug=slug
    )

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    is_judge = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="judge"
    ).exists()

    if not (is_manager or is_judge):
        return redirect(
            "conference_overview",
            slug=conference.slug
        )

    if request.method == "POST":
        submission_id = request.POST.get("submission_id")
        reviewer_role_id = request.POST.get("reviewer_role_id")
        proposed_deadline = request.POST.get("proposed_deadline")

        submission = get_object_or_404(
            Submission,
            id=submission_id,
            conference=conference
        )

        reviewer_role = get_object_or_404(
            ConferenceRole,
            id=reviewer_role_id,
            conference=conference,
            role="content_reviewer"
        )

        assignment, created = ReviewAssignment.objects.get_or_create(
            submission=submission,
            reviewer=reviewer_role.user,
            role=reviewer_role.role,
            defaults={
                "proposed_deadline": proposed_deadline or None
            }
        )

        if not created and proposed_deadline:
            assignment.proposed_deadline = proposed_deadline
            assignment.invitation_status = "pending"
            assignment.accepted_deadline = None
            assignment.deadline_extension_requested = False
            assignment.accepted_at = None
            assignment.declined_at = None
            assignment.decline_reason = ""
            assignment.save()

        if created:
            send_event_email(
                "review_invitation",
                submission,
                request=request,
                reviewer=reviewer_role.user,
            )

            send_event_email(
                "review_initiated",
                submission,
                request=request,
            )
            messages.success(request, "Reviewer assigned successfully.")
        else:
            messages.info(request, "This reviewer is already assigned to this paper.")

        submission.status = "under_review"
        submission.save(update_fields=["status", "updated_at"])

        return redirect(
            "conference_submissions",
            slug=conference.slug
        )

    submissions = Submission.objects.filter(
        conference=conference
    ).select_related(
        "author",
        "topic",
        "secondary_topic",
    ).prefetch_related(
        "review_assignments__reviewer"
    ).order_by("-created_at")

    reviewers = ConferenceRole.objects.filter(
        conference=conference,
        role="content_reviewer"
    ).select_related("user").order_by(
        "user__first_name",
        "user__last_name",
        "user__username"
    )

    return render(
        request,
        "conferences/conference_submissions.html",
        {
            "conference": conference,
            "submissions": submissions,
            "reviewers": reviewers,
        }
    )

@login_required
def reviewer_topics(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    reviewer_role = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role__in=["content_reviewer", "layout_reviewer"]
    ).first()

    if not reviewer_role:
        return redirect("conference_overview", slug=conference.slug)

    topics = ConferenceTopic.objects.filter(
        conference=conference,
        enabled=True
    ).order_by("order", "code")

    sidebar_cards = ConferenceSidebarCard.objects.filter(
        conference=conference,
        enabled=True
    ).order_by("order")

    if request.method == "POST":
        selected_topic_ids = request.POST.getlist("topics")
        reviewer_role.topics.set(selected_topic_ids)
        return redirect("reviewer_topics", slug=conference.slug)

    selected_topics = reviewer_role.topics.values_list("id", flat=True)

    return render(request, "conferences/reviewer_topics.html", {
        "conference": conference,
        "topics": topics,
        "selected_topics": selected_topics,
    })


@login_required
def upload_revision(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    # Allow revision upload for:
    # - the account that submitted the paper
    # - the linked author account
    # - the first author email
    # - any co-author email stored in legacy or structured co-author fields
    user_email = (request.user.email or "").strip().lower()

    coauthor_emails = set()

    if getattr(submission, "coauthor_emails", ""):
        for email in str(submission.coauthor_emails).replace(",", "\n").replace(";", "\n").splitlines():
            email = email.strip().lower()
            if email:
                coauthor_emails.add(email)

    for item in (getattr(submission, "coauthors_data", None) or []):
        if isinstance(item, dict):
            email = str(item.get("email", "")).strip().lower()
            if email:
                coauthor_emails.add(email)

    can_upload_revision = (
        submission.author_id == request.user.id
        or getattr(submission, "submitted_by_id", None) == request.user.id
        or user_email == (getattr(submission, "first_author_email", "") or "").strip().lower()
        or user_email in coauthor_emails
    )

    if not can_upload_revision:
        messages.error(request, "You do not have permission to upload a revision for this submission.")
        return redirect("my_submissions")

    allowed_statuses = [
        "revision_required",
        "layout_revision_required",
    ]

    if submission.status not in allowed_statuses:
        messages.error(request, "This submission is not currently open for revision upload.")
        return redirect("my_submissions")

    if request.method == "POST":
        form = RevisionUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = form.cleaned_data["full_paper_file"]
            extension = Path(uploaded_file.name).suffix.lower()
            source_path = None
            anonymized_path = None

            try:
                with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as source_tmp:
                    for chunk in uploaded_file.chunks():
                        source_tmp.write(chunk)
                    source_path = source_tmp.name

                if submission.status == "revision_required":
                    next_round = submission.revision_round or 1
                    revised_public_id = f"media/revised_papers/{submission.paper_code}-r{next_round}"

                    cloudinary.uploader.upload(
                        source_path,
                        resource_type="raw",
                        public_id=revised_public_id,
                        overwrite=True,
                        unique_filename=False,
                        use_filename=True,
                    )

                    submission.revised_paper_file.name = f"revised_papers/{submission.paper_code}-r{next_round}{extension}"
                    submission.full_paper_file.name = f"revised_papers/{submission.paper_code}-r{next_round}{extension}"

                    if extension == ".docx":
                        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as anonymized_tmp:
                            anonymized_path = anonymized_tmp.name

                        anonymize_docx(source_path, anonymized_path)

                        cloudinary.uploader.upload(
                            anonymized_path,
                            resource_type="raw",
                            public_id=f"media/anonymous_papers/{submission.paper_code}-r{next_round}",
                            overwrite=True,
                            unique_filename=False,
                            use_filename=True,
                        )
                        submission.anonymized_paper_file.name = f"anonymous_papers/{submission.paper_code}-r{next_round}.docx"

                    submission.status = "revised_submitted"
                    success_message = "Revised paper uploaded successfully. It is now ready for the judge to review."
                else:
                    next_round = submission.layout_revision_round or 1
                    layout_public_id = f"media/layout_revised_papers/{submission.paper_code}-layout-r{next_round}"

                    cloudinary.uploader.upload(
                        source_path,
                        resource_type="raw",
                        public_id=layout_public_id,
                        overwrite=True,
                        unique_filename=False,
                        use_filename=True,
                    )

                    submission.layout_revised_paper_file.name = f"layout_revised_papers/{submission.paper_code}-layout-r{next_round}{extension}"
                    submission.full_paper_file.name = f"layout_revised_papers/{submission.paper_code}-layout-r{next_round}{extension}"
                    submission.status = "layout_revision_submitted"
                    success_message = "Corrected layout version uploaded successfully. It is now ready for layout review."

                submission.save()

            except Exception as e:
                print("Revision upload/anonymization error:", e)
                messages.error(request, "Revision upload failed. Please try again.")
                return redirect("upload_revision", submission_id=submission.id)

            finally:
                if source_path and os.path.exists(source_path):
                    os.remove(source_path)
                if anonymized_path and os.path.exists(anonymized_path):
                    os.remove(anonymized_path)

            if submission.status == "revised_submitted":
                send_event_email("revision_uploaded", submission, request=request)

                assignments = ReviewAssignment.objects.filter(
                    submission=submission,
                    role="content_reviewer"
                ).select_related("reviewer")

                for assignment in assignments:
                    send_event_email(
                        "rereview_invitation",
                        submission,
                        request=request,
                        reviewer=assignment.reviewer,
                        assignment=assignment,
                    )

            elif submission.status == "layout_revision_submitted":
                send_event_email("layout_correction_submitted", submission, request=request)

            messages.success(request, success_message)
            return redirect("my_submissions")
    else:
        form = RevisionUploadForm()

    return render(request, "conferences/upload_revision.html", {
        "submission": submission,
        "form": form,
    })


@login_required
def layout_dashboard(request):
    layout_roles = ConferenceRole.objects.filter(
        user=request.user,
        role__in=["layout_reviewer", "manager"]
    )

    if not layout_roles.exists():
        return redirect("/")

    conferences = [role.conference for role in layout_roles]

    submissions = Submission.objects.filter(
        conference__in=conferences,
        status__in=[
            "accepted_for_layout",
            "layout_revision_required",
            "layout_revision_submitted",
        ]
    ).select_related(
        "conference",
        "author",
        "topic",
        "secondary_topic",
    ).order_by("-updated_at")

    accepted_publication_submissions = Submission.objects.filter(
        conference__in=conferences,
        status="final_accepted"
    ).select_related(
        "conference",
        "author",
        "topic",
        "secondary_topic",
    ).prefetch_related(
        "reviews__reviewer"
    ).order_by("-updated_at")

    return render(request, "conferences/layout_dashboard.html", {
        "submissions": submissions,
        "accepted_publication_submissions": accepted_publication_submissions,
    })


@login_required
def layout_decision(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    can_layout_review = ConferenceRole.objects.filter(
        user=request.user,
        conference=submission.conference,
        role__in=["layout_reviewer", "manager"]
    ).exists()

    if not can_layout_review:
        return redirect("/")

    if submission.status not in ["accepted_for_layout", "layout_revision_submitted", "layout_revision_required"]:
        messages.error(request, "This submission is not currently in layout review.")
        return redirect("layout_dashboard")

    if request.method == "POST":
        form = LayoutDecisionForm(request.POST)

        if form.is_valid():
            status = form.cleaned_data["status"]
            comment = form.cleaned_data["comment"]

            submission.status = status
            submission.final_comment = comment

            if status == "layout_revision_required":
                submission.layout_revision_message = comment
                submission.layout_revision_round += 1

            submission.save()

            if status == "layout_revision_required":
                send_event_email("layout_correction_needed", submission, request=request)
            elif status == "final_accepted":
                send_event_email("manuscript_accepted", submission, request=request)

            messages.success(request, "Layout decision saved successfully.")
            return redirect("layout_dashboard")
    else:
        form = LayoutDecisionForm(initial={
            "status": "final_accepted",
            "comment": submission.layout_revision_message,
        })

    return render(request, "conferences/layout_decision.html", {
        "submission": submission,
        "form": form,
    })


@login_required
def footer_settings(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("conference_overview", slug=conference.slug)

    if request.method == "POST":
        form = ConferenceFooterForm(request.POST, request.FILES, instance=conference)
        if form.is_valid():
            form.save()
            messages.success(request, "Footer settings updated successfully.")
            return redirect("footer_settings", slug=conference.slug)
    else:
        form = ConferenceFooterForm(instance=conference)

    partners = ConferenceFooterPartner.objects.filter(
        conference=conference
    ).order_by("order", "name")

    partner_form = ConferenceFooterPartnerForm()

    return render(request, "conferences/footer_settings.html", {
        "conference": conference,
        "form": form,
        "partners": partners,
        "partner_form": partner_form,
    })


@login_required
def add_footer_partner(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("conference_overview", slug=conference.slug)

    if request.method == "POST":
        form = ConferenceFooterPartnerForm(request.POST, request.FILES)
        if form.is_valid():
            partner = form.save(commit=False)
            partner.conference = conference
            partner.save()
            messages.success(request, "Footer organization added successfully.")
        else:
            messages.error(request, "Footer organization could not be saved. Please check the form.")

    return redirect("footer_settings", slug=conference.slug)


@login_required
def edit_footer_partner(request, partner_id):
    partner = get_object_or_404(ConferenceFooterPartner, id=partner_id)
    conference = partner.conference

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("conference_overview", slug=conference.slug)

    if request.method == "POST":
        form = ConferenceFooterPartnerForm(request.POST, request.FILES, instance=partner)
        if form.is_valid():
            form.save()
            messages.success(request, "Footer organization updated successfully.")
            return redirect("footer_settings", slug=conference.slug)
    else:
        form = ConferenceFooterPartnerForm(instance=partner)

    return render(request, "conferences/footer_partner_form.html", {
        "conference": conference,
        "partner": partner,
        "form": form,
    })


@login_required
def delete_footer_partner(request, partner_id):
    partner = get_object_or_404(ConferenceFooterPartner, id=partner_id)
    conference = partner.conference

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("conference_overview", slug=conference.slug)

    if request.method == "POST":
        partner.delete()
        messages.success(request, "Footer organization deleted successfully.")
        return redirect("footer_settings", slug=conference.slug)

    return render(request, "conferences/delete_footer_partner.html", {
        "conference": conference,
        "partner": partner,
    })


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            UserProfile.objects.create(
                user=user,
                affiliation=form.cleaned_data["affiliation"],
                title=form.cleaned_data["title"],
                country=form.cleaned_data["country"],
            )

            login(request, user)

            return redirect("/")
    else:
        form = RegisterForm()

    return render(request, "conferences/register.html", {
        "form": form
    })



@login_required
def download_review_paper(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    is_assigned_reviewer = ReviewAssignment.objects.filter(
        submission=submission,
        reviewer=request.user,
        role="content_reviewer"
    ).exists()

    if not is_assigned_reviewer:
        messages.error(request, "You do not have permission to download this review file.")
        return redirect("my_reviews")

    if submission.anonymized_paper_file:
        return redirect(submission.anonymized_paper_file.url)

    if not submission.full_paper_file:
        messages.error(request, "No paper file is available for this submission.")
        return redirect("my_reviews")

    extension = Path(submission.full_paper_file.name).suffix.lower()

    if extension != ".docx":
        messages.error(
            request,
            "An anonymized reviewer file is not available for this submission. Please contact the conference manager."
        )
        return redirect("my_reviews")

    source_path = None
    anonymized_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as source_tmp:
            source_path = source_tmp.name

        urllib.request.urlretrieve(submission.full_paper_file.url, source_path)

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as anonymized_tmp:
            anonymized_path = anonymized_tmp.name

        anonymize_docx(source_path, anonymized_path)

        public_id = f"media/anonymous_papers/{submission.paper_code}"
        cloudinary.uploader.upload(
            anonymized_path,
            resource_type="raw",
            public_id=public_id,
            overwrite=True,
            unique_filename=False,
            use_filename=True,
        )

        submission.anonymized_paper_file.name = f"anonymous_papers/{submission.paper_code}.docx"
        submission.save(update_fields=["anonymized_paper_file", "updated_at"])

        return redirect(submission.anonymized_paper_file.url)

    except Exception as e:
        print("Reviewer paper download/anonymization error:", e)
        messages.error(request, "Could not prepare the anonymized reviewer file. Please contact the conference manager.")
        return redirect("my_reviews")

    finally:
        if source_path and os.path.exists(source_path):
            os.remove(source_path)
        if anonymized_path and os.path.exists(anonymized_path):
            os.remove(anonymized_path)

@login_required
def my_reviews(request):
    assignments = ReviewAssignment.objects.filter(
        reviewer=request.user,
        role="content_reviewer",
        submission__status__in=["under_review", "revised_submitted", "revision_required"]
    ).select_related(
        "submission",
        "submission__conference",
        "submission__topic",
        "submission__secondary_topic",
    ).order_by("submission__conference__title_en", "submission__title")

    return render(request, "conferences/my_reviews.html", {
        "assignments": assignments,
    })
@login_required
def reviewer_dashboard(request):
    assignments = ReviewAssignment.objects.filter(
        reviewer=request.user,
        role="content_reviewer",
        submission__status__in=["under_review", "revised_submitted", "revision_required"]
    ).select_related(
        "submission",
        "submission__conference",
        "submission__topic",
        "submission__secondary_topic",
    ).order_by("submission__conference__title_en", "submission__title")

    return render(request, "conferences/reviewer_dashboard.html", {
        "assignments": assignments,
    })
@login_required
def conference_people(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    can_manage_people = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role__in=["manager", "judge"]
    ).exists()

    if not can_manage_people:
        return redirect("conference_overview", slug=conference.slug)

    role_options = [
        ("manager", "Paper manager"),
        ("judge", "Judge"),
        ("content_reviewer", "Content reviewer"),
        ("layout_reviewer", "Layout reviewer"),
    ]

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        role = request.POST.get("role")
        action = request.POST.get("action")

        selected_user = get_object_or_404(User, id=user_id)

        if role in dict(role_options):
            if action == "add":
                ConferenceRole.objects.get_or_create(
                    conference=conference,
                    user=selected_user,
                    role=role
                )

            elif action == "remove":
                ConferenceRole.objects.filter(
                    conference=conference,
                    user=selected_user,
                    role=role
                ).delete()

        return redirect("conference_people", slug=conference.slug)

    query = request.GET.get("q", "").strip()

    users = User.objects.all().order_by("first_name", "last_name", "username")

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(profile__affiliation__icontains=query)
        )

    roles = ConferenceRole.objects.filter(
        conference=conference
    ).select_related("user", "user__profile")

    role_map = {}
    for conference_role in roles:
        role_map.setdefault(conference_role.user_id, set()).add(conference_role.role)

    people = []

    for user in users:
        people.append({
            "user": user,
            "roles": role_map.get(user.id, set()),
        })

    grouped_roles = {
        "manager": roles.filter(role="manager"),
        "judge": roles.filter(role="judge"),
        "content_reviewer": roles.filter(role="content_reviewer"),
        "layout_reviewer": roles.filter(role="layout_reviewer"),
    }

    return render(request, "conferences/conference_people.html", {
        "conference": conference,
        "people": people,
        "role_options": role_options,
        "grouped_roles": grouped_roles,
        "query": query,
    })
@login_required
def delete_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    is_manager = ConferenceRole.objects.filter(
        conference=submission.conference,
        user=request.user,
        role="manager"
    ).exists()

    is_judge = ConferenceRole.objects.filter(
        conference=submission.conference,
        user=request.user,
        role="judge"
    ).exists()

    if not (is_manager or is_judge):
        return redirect("conference_overview", slug=submission.conference.slug)

    if request.method == "POST":
        submission.delete()

        messages.success(request, "Submission deleted successfully.")

        return redirect(
            "conference_submissions",
            slug=submission.conference.slug
        )

    return render(request, "conferences/delete_submission.html", {
        "submission": submission
    })

@login_required
def email_health_dashboard(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    can_manage = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role__in=["manager", "judge"]
    ).exists()

    if not can_manage:
        return redirect("/")

    if request.method == "POST":
        result = process_scheduled_review_emails(conference=conference, request=request)
        messages.success(
            request,
            f"Email automation checked. Due soon sent: {result['due_soon_sent']}; overdue sent: {result['overdue_sent']}; skipped: {result['skipped']}."
        )
        return redirect("email_health_dashboard", slug=conference.slug)

    status = get_email_workflow_status(conference)

    logs = EmailLog.objects.filter(
        conference=conference
    ).select_related("submission", "template").order_by("-created_at")[:100]

    failed_logs = logs.filter(status="failed")[:20] if hasattr(logs, "filter") else []

    return render(request, "conferences/email_health_dashboard.html", {
        "conference": conference,
        "status": status,
        "logs": logs,
        "failed_logs": failed_logs,
    })


@login_required
def run_email_automation_now(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    can_manage = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role__in=["manager", "judge"]
    ).exists()

    if not can_manage:
        return redirect("/")

    result = process_scheduled_review_emails(conference=conference, request=request)
    messages.success(
        request,
        f"Email automation completed. Due soon sent: {result['due_soon_sent']}; overdue sent: {result['overdue_sent']}; skipped: {result['skipped']}."
    )
    return redirect("email_health_dashboard", slug=conference.slug)

def terms_of_use(request):
    return render(request, "conferences/terms_of_use.html")


def privacy_policy(request):
    return render(request, "conferences/privacy_policy.html")
