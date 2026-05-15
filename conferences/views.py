
import os
import tempfile
import urllib.request
from datetime import timedelta
import cloudinary.uploader

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

from .emails import send_event_email, preview_template, send_test_template_email
from .email_defaults import OFFICIAL_EMAIL_EVENTS
from .utils import anonymize_docx
from .document_storage import save_local_file_to_field, cleanup_submission_temporary_files
from .storage_backends import get_supabase_storage_usage


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
        UserProfile.objects.all()
        .exclude(country="")
        .values_list("country", flat=True)
        .distinct()
    )

    country_set.update(str(country).strip() for country in registered_countries if str(country).strip())

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

            # Official Green Building email workflow:
            # 11. Notify reviewers about the editor/judge decision.
            # 12. Notify authors that the review stage has been completed.
            accepted_assignments = ReviewAssignment.objects.filter(
                submission=submission,
                role="content_reviewer",
                invitation_status="accepted",
            ).select_related("reviewer")

            for assignment in accepted_assignments:
                send_event_email(
                    "reviewer_editor_decision",
                    submission,
                    request=request,
                    reviewer=assignment.reviewer,
                    assignment=assignment,
                )

            send_event_email("review_completed_author", submission, request=request)

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
def assign_papers(request, slug, submission_id=None):
    conference = get_object_or_404(Conference, slug=slug)

    can_assign = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="judge"
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

    selected_submission = None
    if submission_id:
        selected_submission = get_object_or_404(
            submissions,
            id=submission_id
        )
        submissions = submissions.filter(id=selected_submission.id)

    reviewers = ConferenceRole.objects.filter(
        conference=conference,
        role="content_reviewer"
    ).select_related("user").prefetch_related("topics")

    if request.method == "POST":
        post_submission_id = request.POST.get("submission_id")
        reviewer_role_id = request.POST.get("reviewer_role_id")
        proposed_deadline = request.POST.get("proposed_deadline")
        review_days = request.POST.get("review_days")

        submission = get_object_or_404(
            Submission,
            id=post_submission_id,
            conference=conference
        )

        reviewer_role = get_object_or_404(
            ConferenceRole,
            id=reviewer_role_id,
            conference=conference,
            role="content_reviewer",
        )

        deadline_date = None
        if proposed_deadline:
            try:
                deadline_date = timezone.datetime.strptime(proposed_deadline, "%Y-%m-%d").date()
            except ValueError:
                deadline_date = None

        if deadline_date is None and review_days:
            try:
                deadline_date = timezone.now().date() + timedelta(days=int(review_days))
            except (TypeError, ValueError):
                deadline_date = None

        if deadline_date is None:
            deadline_date = conference.review_deadline or (timezone.now().date() + timedelta(days=10))

        assignment, created = ReviewAssignment.objects.get_or_create(
            submission=submission,
            reviewer=reviewer_role.user,
            role=reviewer_role.role,
            defaults={
                "invitation_status": "pending",
                "proposed_deadline": deadline_date,
                "review_invitation_sent_at": timezone.now(),
            }
        )

        if not created:
            assignment.invitation_status = "pending"
            assignment.proposed_deadline = deadline_date
            assignment.accepted_deadline = None
            assignment.deadline_extension_requested = False
            assignment.decline_reason = ""
            assignment.review_invitation_sent_at = timezone.now()
            assignment.accepted_at = None
            assignment.declined_at = None
            assignment.due_soon_reminder_sent = False
            assignment.overdue_reminder_sent = False
            assignment.save()

        send_event_email(
            "review_invitation",
            submission,
            request=request,
            reviewer=reviewer_role.user,
            assignment=assignment,
        )

        messages.success(request, "Review invitation sent to reviewer.")

        if submission_id:
            return redirect("assign_paper_single", slug=conference.slug, submission_id=submission.id)
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
        "selected_submission": selected_submission,
    })

@login_required
def review_invitation_response(request, assignment_id):
    assignment = get_object_or_404(
        ReviewAssignment.objects.select_related(
            "submission",
            "submission__conference",
            "submission__topic",
            "submission__secondary_topic",
            "reviewer",
        ),
        id=assignment_id,
        reviewer=request.user,
        role="content_reviewer",
    )

    submission = assignment.submission

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "decline":
            assignment.invitation_status = "declined"
            assignment.declined_at = timezone.now()
            assignment.decline_reason = request.POST.get("decline_reason", "").strip()
            assignment.save()
            messages.success(request, "You have declined this review invitation.")
            return redirect("my_reviews")

        if action == "accept":
            deadline_choice = request.POST.get("deadline_choice", "proposed")
            requested_deadline = request.POST.get("requested_deadline")
            final_deadline = assignment.proposed_deadline or submission.conference.review_deadline
            extension_requested = False

            if deadline_choice == "custom" and requested_deadline:
                try:
                    final_deadline = timezone.datetime.strptime(requested_deadline, "%Y-%m-%d").date()
                    extension_requested = True
                except ValueError:
                    messages.error(request, "Please select a valid requested deadline.")
                    return redirect("review_invitation_response", assignment_id=assignment.id)

            assignment.invitation_status = "accepted"
            assignment.accepted_at = timezone.now()
            assignment.accepted_deadline = final_deadline
            assignment.deadline_extension_requested = extension_requested
            assignment.save()

            if submission.status == "submitted":
                submission.status = "under_review"
                submission.save(update_fields=["status", "updated_at"])

            send_event_email(
                "review_request_accepted",
                submission,
                request=request,
                reviewer=request.user,
                assignment=assignment,
            )
            send_event_email(
                "review_initiated",
                submission,
                request=request,
            )

            messages.success(request, "Review invitation accepted. You can now access the review form.")
            return redirect("review_submission", submission_id=submission.id)

    return render(request, "conferences/review_invitation_response.html", {
        "assignment": assignment,
        "submission": submission,
        "conference": submission.conference,
    })

@login_required
def review_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    assignment = ReviewAssignment.objects.filter(
        submission=submission,
        reviewer=request.user,
        role="content_reviewer",
        invitation_status="accepted",
    ).first()

    if not assignment:
        messages.error(request, "You must accept the review invitation before opening the review form.")
        return redirect("my_reviews")

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

            send_event_email(
                "review_received",
                submission,
                request=request,
                reviewer=request.user,
                assignment=assignment,
            )

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

    assignments = ReviewAssignment.objects.filter(
        submission=submission,
        role="content_reviewer",
        invitation_status="accepted",
    ).select_related("reviewer")

    reviewer_count = assignments.count()

    if reviewer_count == 0:
        messages.error(request, "No accepted content reviewers are assigned to this submission. Assign reviewers first.")
        return redirect("submission_result", submission_id=submission.id)

    submission.status = "under_review"
    submission.save(update_fields=["status", "updated_at"])

    for assignment in assignments:
        send_event_email(
            "rereview_invitation",
            submission,
            request=request,
            reviewer=assignment.reviewer,
            assignment=assignment,
        )

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

    from .email_defaults import DEFAULT_EMAIL_TEMPLATES_2026

    for event, template_data in DEFAULT_EMAIL_TEMPLATES_2026.items():
        EmailTemplate.objects.get_or_create(
            conference=conference,
            event=event,
            defaults={
                "enabled": template_data.get("enabled", True),
                "send_to_author": template_data.get("send_to_author", True),
                "send_to_coauthors": template_data.get("send_to_coauthors", False),
                "send_to_reviewer": template_data.get("send_to_reviewer", False),
                "send_to_managers": template_data.get("send_to_managers", False),
                "send_to_layout_reviewers": template_data.get("send_to_layout_reviewers", False),
                "subject": template_data["subject"],
                "body": template_data["body"],
            }
        )

    templates_qs = EmailTemplate.objects.filter(
        conference=conference,
        event__in=OFFICIAL_EMAIL_EVENTS,
    )

    templates_by_event = {
        template.event: template
        for template in templates_qs
    }

    templates = [
        templates_by_event[event]
        for event in OFFICIAL_EMAIL_EVENTS
        if event in templates_by_event
    ]

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
def send_test_email_template(request, template_id):
    template = get_object_or_404(EmailTemplate, id=template_id)
    conference = template.conference

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
        return redirect("/")

    if request.method != "POST":
        return redirect("email_templates", slug=conference.slug)

    recipient = request.POST.get("test_recipient") or request.user.email
    ok, message = send_test_template_email(template, recipient, request=request)

    if ok:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("email_templates", slug=conference.slug)


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

                # Generate paper code
                existing_count = (
                    Submission.objects.filter(conference=conference).count() + 1
                )

                conference_code = conference.slug.replace("-", "").upper()[:6]

                submission.paper_code = (
                    f"{conference_code}-{existing_count:03d}"
                )

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

                        save_local_file_to_field(
                            submission.full_paper_file,
                            source_path,
                            f"originals/{submission.paper_code}_submission_{submission.id}{extension}",
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

                            save_local_file_to_field(
                                submission.anonymized_paper_file,
                                anonymized_path,
                                f"{submission.paper_code}_submission_{submission.id}.docx",
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

    submissions = Submission.objects.filter(
        conference=conference
    ).select_related(
        "author",
        "topic",
        "secondary_topic",
    ).order_by("-created_at")

    return render(
        request,
        "conferences/conference_submissions.html",
        {
            "conference": conference,
            "submissions": submissions,
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
    submission = get_object_or_404(Submission, id=submission_id, author=request.user)

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

                    revised_storage_name = f"{submission.paper_code}-r{next_round}{extension}"
                    save_local_file_to_field(
                        submission.revised_paper_file,
                        source_path,
                        revised_storage_name,
                    )
                    save_local_file_to_field(
                        submission.full_paper_file,
                        source_path,
                        revised_storage_name,
                    )

                    if extension == ".docx":
                        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as anonymized_tmp:
                            anonymized_path = anonymized_tmp.name

                        anonymize_docx(source_path, anonymized_path)

                        save_local_file_to_field(
                            submission.anonymized_paper_file,
                            anonymized_path,
                            f"{submission.paper_code}-r{next_round}.docx",
                        )

                    submission.status = "revised_submitted"
                    success_message = "Revised paper uploaded successfully. It is now ready for the judge to review."
                else:
                    next_round = submission.layout_revision_round or 1
                    layout_public_id = f"media/layout_revised_papers/{submission.paper_code}-layout-r{next_round}"

                    layout_storage_name = f"{submission.paper_code}-layout-r{next_round}{extension}"
                    save_local_file_to_field(
                        submission.layout_revised_paper_file,
                        source_path,
                        layout_storage_name,
                    )
                    save_local_file_to_field(
                        submission.full_paper_file,
                        source_path,
                        layout_storage_name,
                    )
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

    return render(request, "conferences/layout_dashboard.html", {
        "submissions": submissions,
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
        form = LayoutDecisionForm(request.POST, request.FILES)

        if form.is_valid():
            status = form.cleaned_data["status"]
            comment = form.cleaned_data["comment"]

            submission.status = status
            submission.final_comment = comment

            final_publication_file = form.cleaned_data.get("final_publication_file")
            if final_publication_file:
                extension = Path(final_publication_file.name).suffix.lower()
                submission.final_publication_file.save(
                    f"{submission.paper_code}-final{extension}",
                    final_publication_file,
                    save=False,
                )

            if status == "layout_revision_required":
                submission.layout_revision_message = comment
                submission.layout_revision_round += 1

            submission.save()

            if status == "layout_revision_required":
                send_event_email("layout_correction_needed", submission, request=request)
            elif status == "final_accepted":
                send_event_email("manuscript_accepted", submission, request=request)
                cleanup_submission_temporary_files(submission)

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


@login_required
def storage_status(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role__in=["manager", "judge"]
    ).exists()

    if not is_manager:
        return redirect("conference_overview", slug=conference.slug)

    supabase_usage = get_supabase_storage_usage()

    cloudinary_fallback_files = 0
    supabase_files_in_db = 0

    file_fields = [
        "full_paper_file",
        "revised_paper_file",
        "layout_revised_paper_file",
        "final_publication_file",
        "anonymized_paper_file",
    ]

    for submission in Submission.objects.filter(conference=conference):
        for field_name in file_fields:
            field = getattr(submission, field_name, None)
            name = getattr(field, "name", "") or ""
            if name.startswith("supabase:"):
                supabase_files_in_db += 1
            elif name:
                cloudinary_fallback_files += 1

    reviewer_file_names = Review.objects.filter(
        submission__conference=conference
    ).exclude(
        commented_paper_file=""
    ).values_list("commented_paper_file", flat=True)

    for name in reviewer_file_names:
        name = str(name or "")
        if name.startswith("supabase:"):
            supabase_files_in_db += 1
        elif name:
            cloudinary_fallback_files += 1

    return render(request, "conferences/storage_status.html", {
        "conference": conference,
        "supabase_usage": supabase_usage,
        "supabase_files_in_db": supabase_files_in_db,
        "cloudinary_fallback_files": cloudinary_fallback_files,
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
        role="content_reviewer",
        invitation_status="accepted",
    ).exists()

    if not is_assigned_reviewer:
        messages.error(request, "You must accept the review invitation before downloading the reviewer file.")
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
        save_local_file_to_field(
            submission.anonymized_paper_file,
            anonymized_path,
            f"{submission.paper_code}.docx",
        )
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
    ).exclude(
        invitation_status="declined"
    ).select_related(
        "submission",
        "submission__conference",
        "submission__topic",
        "submission__secondary_topic",
    ).order_by("invitation_status", "submission__conference__title_en", "submission__title")

    return render(request, "conferences/my_reviews.html", {
        "assignments": assignments,
    })

@login_required
def reviewer_dashboard(request):
    assignments = ReviewAssignment.objects.filter(
        reviewer=request.user,
        role="content_reviewer",
    ).exclude(
        invitation_status="declined"
    ).select_related(
        "submission",
        "submission__conference",
        "submission__topic",
        "submission__secondary_topic",
    ).order_by("invitation_status", "submission__conference__title_en", "submission__title")

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