
import os
import tempfile
import urllib.request
from django.http import HttpResponse
from django.core.files import File
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.db import transaction
from django.core.mail import send_mail
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from pathlib import Path
from datetime import datetime, timedelta

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
    AccountSettingsForm,
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


REQUIRED_ACCEPTED_CONTENT_REVIEWERS = 2
REVIEWER_DEADLINE_EXTENSION_DAYS = 5
CONTENT_REVIEW_START_STATUSES = {
    "submitted",
    "reviewer_acceptance_pending",
    "under_review",
}


def get_reviewer_deadline_bounds(assignment):
    """Return the deadline set for the reviewer and the latest allowed requested deadline."""
    base_deadline = assignment.proposed_deadline or assignment.submission.conference.review_deadline

    if not base_deadline:
        return None, None

    return base_deadline, base_deadline + timedelta(days=REVIEWER_DEADLINE_EXTENSION_DAYS)


def parse_proposed_review_deadline(raw_deadline, conference):
    """Use the judge-selected deadline, or the conference review deadline as a fallback."""
    if raw_deadline:
        try:
            return datetime.strptime(raw_deadline, "%Y-%m-%d").date(), None
        except ValueError:
            return None, "Invalid proposed review deadline format."

    if conference.review_deadline:
        return conference.review_deadline, None

    return None, "Please set a proposed review deadline before assigning a reviewer."


def accepted_content_reviewer_count(submission):
    return ReviewAssignment.objects.filter(
        submission=submission,
        role="content_reviewer",
        invitation_status="accepted",
    ).values("reviewer_id").distinct().count()


def sync_content_review_start_status(submission):
    """Keep the paper before content review until at least two reviewers accept."""
    if submission.status not in CONTENT_REVIEW_START_STATUSES:
        return False

    assignments = ReviewAssignment.objects.filter(
        submission=submission,
        role="content_reviewer",
    )

    if not assignments.exists():
        return False

    accepted_count = assignments.filter(
        invitation_status="accepted",
    ).values("reviewer_id").distinct().count()

    next_status = (
        "under_review"
        if accepted_count >= REQUIRED_ACCEPTED_CONTENT_REVIEWERS
        else "reviewer_acceptance_pending"
    )

    if submission.status == next_status:
        return False

    submission.status = next_status
    submission.save(update_fields=["status", "updated_at"])
    return next_status == "under_review"


def mark_content_review_completed_if_ready(submission):
    current_round = submission.revision_round or 0

    accepted_assignments = ReviewAssignment.objects.filter(
        submission=submission,
        role="content_reviewer",
        invitation_status="accepted",
    )

    accepted_reviewer_ids = accepted_assignments.values_list(
        "reviewer_id",
        flat=True,
    )

    accepted_reviewers_count = accepted_assignments.values(
        "reviewer_id"
    ).distinct().count()

    completed_reviews_count = Review.objects.filter(
        submission=submission,
        review_round=current_round,
        reviewer_id__in=accepted_reviewer_ids,
    ).values("reviewer").distinct().count()

    if (
        submission.status == "under_review"
        and accepted_reviewers_count >= REQUIRED_ACCEPTED_CONTENT_REVIEWERS
        and completed_reviews_count >= accepted_reviewers_count
    ):
        submission.status = "reviewed_by_reviewer"
        submission.save(update_fields=["status", "updated_at"])
        return True

    return False


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
    base_review_deadline, max_requested_deadline = get_reviewer_deadline_bounds(assignment)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "accept":
            deadline_choice = request.POST.get("deadline_choice", "proposed")

            assignment.invitation_status = "accepted"
            assignment.accepted_at = timezone.now()

            if deadline_choice == "proposed":
                assignment.accepted_deadline = base_review_deadline
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

                if base_review_deadline and parsed_date < base_review_deadline:
                    messages.error(
                        request,
                        "Requested deadline cannot be earlier than the deadline set for this review."
                    )
                    return redirect(
                        "review_invitation_response",
                        assignment_id=assignment.id
                    )

                if max_requested_deadline and parsed_date > max_requested_deadline:
                    messages.error(
                        request,
                        (
                            "Reviewers may move the review deadline by a maximum of "
                            f"{REVIEWER_DEADLINE_EXTENSION_DAYS} days. "
                            f"Please select a date no later than {max_requested_deadline.strftime('%d.%m.%Y.')}"
                        )
                    )
                    return redirect(
                        "review_invitation_response",
                        assignment_id=assignment.id
                    )

                assignment.accepted_deadline = parsed_date
                assignment.deadline_extension_requested = True

            assignment.save()

            if sync_content_review_start_status(submission):
                send_event_email(
                    "review_initiated",
                    submission,
                    request=request,
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

            # Declined reviewers remain visible in Judge Dashboard,
            # but only accepted reviewers count toward the active review workflow.
            sync_content_review_start_status(submission)
            mark_content_review_completed_if_ready(submission)

            decline_extra = {
                "decline_reason": assignment.decline_reason,
            }

            send_event_email(
                "review_declined_judge",
                submission,
                request=request,
                reviewer=request.user,
                assignment=assignment,
                extra=decline_extra,
            )

            send_event_email(
                "review_declined_author",
                submission,
                request=request,
                reviewer=request.user,
                assignment=assignment,
                extra=decline_extra,
            )

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
            "base_review_deadline": base_review_deadline,
            "max_requested_deadline": max_requested_deadline,
            "reviewer_deadline_extension_days": REVIEWER_DEADLINE_EXTENSION_DAYS,
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
            selected_status = form.cleaned_data["status"]
            comment = form.cleaned_data["comment"]
            revision_deadline = form.cleaned_data.get("revision_deadline")

            # In the Judge decision workflow, both minor and major revisions
            # mean that the AUTHOR must revise the manuscript.
            # Layout revision is handled later by the layout reviewer.
            if selected_status == "minor_revision":
                status = "revision_required"
            else:
                status = selected_status

            submission.status = status
            submission.judge_decision = selected_status
            submission.final_comment = comment

            # Keep the review round that the editor is deciding on.
            # If the decision is revision_required, revision_round is increased
            # below for the NEXT review cycle, so email comments must still be
            # collected from this saved decision_review_round.
            decision_review_round = submission.revision_round or 0

            if status == "revision_required":
                submission.judge_revision_message = comment
                submission.author_revision_deadline = revision_deadline
                submission.revision_round += 1

            submission.save()

            editor_decision_labels = {
                "accepted_for_layout": "Accept in present form",
                "minor_revision": "Accept after minor revision",
                "revision_required": "Reconsider after major revision",
                "rejected": "Reject",
            }

            editor_comments_for_email = submission.final_comment or ""

            if status == "revision_required":
                my_submissions_link = request.build_absolute_uri(
                    reverse("my_submissions")
                )

                revision_notice = (
                    "\n\nPlease upload your revised manuscript through "
                    f"My submissions: {my_submissions_link}"
                )

                editor_comments_for_email = (
                    editor_comments_for_email + revision_notice
                    if editor_comments_for_email
                    else revision_notice.strip()
                )

            # Email comments must come only from the review round that has
            # just been evaluated by the editor, not from older rounds.
            decision_reviews_for_email = Review.objects.filter(
                submission=submission,
                review_round=decision_review_round,
            ).select_related(
                "reviewer",
                "reviewer__profile"
            ).order_by(
                "reviewer_id"
            )

            reviewer_author_comment_lines = []
            visible_reviewer_number = 1

            for review_for_email in decision_reviews_for_email:
                comment_for_author = (review_for_email.comments_for_authors or "").strip()

                if not comment_for_author:
                    continue

                reviewer_author_comment_lines.append(
                    f"Reviewer {visible_reviewer_number}:\n"
                    f"{comment_for_author}"
                )
                visible_reviewer_number += 1

            reviewer_comments_for_authors = "\n\n".join(
                reviewer_author_comment_lines
            )

            decision_email_extra = {
                "editor_decision": editor_decision_labels.get(
                    selected_status,
                    submission.get_status_display()
                ),
                "editor_comments": editor_comments_for_email,
                "reviewer_comments": reviewer_comments_for_authors,
            }

            # Separate context for Email 11 — reviewer notification.
            # Reviewers receive the editor decision, editor comments and all
            # anonymous reviewer comments from the current decision round only.
            # They do not receive author-only revision upload instructions.
            reviewer_decision_email_extra = {
                "editor_decision": editor_decision_labels.get(
                    selected_status,
                    submission.get_status_display()
                ),
                "editor_comments": submission.final_comment or "",
                "reviewer_comments": reviewer_comments_for_authors,
            }

            if status == "revision_required":
                send_event_email(
                    "review_completed_author",
                    submission,
                    request=request,
                    extra=decision_email_extra,
                )
            elif status == "accepted_for_layout":
                send_event_email(
                    "accepted_for_layout",
                    submission,
                    request=request,
                    extra=decision_email_extra,
                )
            elif status == "rejected":
                send_event_email(
                    "rejected",
                    submission,
                    request=request,
                    extra=decision_email_extra,
                )

            # Email 11: notify only reviewers who explicitly selected
            # "yes" for final editor-decision notification in their review.
            notified_reviewer_ids = set()
            reviewer_notification_reviews = Review.objects.filter(
                submission=submission,
                review_round=decision_review_round,
                wants_final_notification="yes",
            ).select_related(
                "reviewer"
            ).order_by(
                "reviewer_id",
            )

            for notification_review in reviewer_notification_reviews:
                if notification_review.reviewer_id in notified_reviewer_ids:
                    continue

                notified_reviewer_ids.add(notification_review.reviewer_id)

                send_event_email(
                    "reviewer_editor_decision",
                    submission,
                    request=request,
                    reviewer=notification_review.reviewer,
                    extra=reviewer_decision_email_extra,
                )

            messages.success(request, "Decision saved successfully.")
            return redirect("submission_result", submission_id=submission.id)
    else:
        form = JudgeDecisionForm(initial={
            "status": submission.judge_decision or (
                submission.status
                if submission.status in ["accepted_for_layout", "revision_required", "rejected"]
                else "accepted_for_layout"
            ),
            "comment": submission.final_comment,
            "revision_deadline": submission.author_revision_deadline,
        })

    decision_reviews = Review.objects.filter(
        submission=submission
    ).select_related(
        "reviewer",
        "reviewer__profile"
    ).order_by(
        "review_round",
        "reviewer_id"
    )

    return render(request, "conferences/make_decision.html", {
        "submission": submission,
        "form": form,
        "decision_reviews": decision_reviews,
    })


@login_required
def assign_papers(request, slug, submission_id=None):
    conference = get_object_or_404(Conference, slug=slug)

    can_assign = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role__in=["manager", "judge"]
    ).exists()

    if not can_assign:
        return redirect("/")

    reviewers = ConferenceRole.objects.filter(
        conference=conference,
        role="content_reviewer"
    ).select_related(
        "user"
    ).prefetch_related(
        "topics"
    ).annotate(
        assigned_papers_count=Count(
            "user__review_assignments__submission",
            filter=Q(
                user__review_assignments__submission__conference=conference,
                user__review_assignments__role="content_reviewer",
            ),
            distinct=True,
        )
    ).order_by(
        "user__first_name",
        "user__last_name",
        "user__username"
    )

    if request.method == "POST":
        posted_submission_id = request.POST.get("submission_id") or submission_id
        reviewer_role_id = request.POST.get("reviewer_role_id")
        proposed_deadline, deadline_error = parse_proposed_review_deadline(
            request.POST.get("proposed_deadline"),
            conference,
        )

        if not posted_submission_id:
            messages.error(request, "No paper was selected for reviewer assignment.")
            return redirect("conference_submissions", slug=conference.slug)

        if deadline_error:
            messages.error(request, deadline_error)
            return redirect(f"/conference/{conference.slug}/assign/{posted_submission_id}/")

        if not reviewer_role_id:
            messages.error(request, "Please select a reviewer before assigning.")
            return redirect(f"/conference/{conference.slug}/assign/{posted_submission_id}/")

        submission = get_object_or_404(
            Submission,
            id=posted_submission_id,
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

        if not created:
            if proposed_deadline:
                assignment.proposed_deadline = proposed_deadline

            assignment.invitation_status = "pending"
            assignment.accepted_deadline = None
            assignment.deadline_extension_requested = False
            assignment.accepted_at = None
            assignment.declined_at = None
            assignment.decline_reason = ""
            assignment.due_soon_reminder_sent = False
            assignment.overdue_reminder_sent = False
            assignment.save()

        if created:
            send_event_email(
                "review_invitation",
                submission,
                request=request,
                reviewer=reviewer_role.user,
            )

            messages.success(request, "Reviewer assigned successfully.")
        else:
            messages.info(
                request,
                "This reviewer was already assigned. The invitation status was reset to pending."
            )

        if sync_content_review_start_status(submission):
            send_event_email(
                "review_initiated",
                submission,
                request=request,
            )

        return redirect(f"/conference/{conference.slug}/assign/{submission.id}/")

    submissions = Submission.objects.filter(
        conference=conference
    ).select_related(
        "author",
        "topic",
        "secondary_topic"
    ).prefetch_related(
        "review_assignments__reviewer"
    )

    if submission_id is not None:
        submission = get_object_or_404(
            submissions,
            id=submission_id
        )

        submission.coauthor_rows = []

        names = [
            x.strip()
            for x in (submission.coauthors or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        titles = [
            x.strip()
            for x in (submission.coauthor_titles or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        for i, name in enumerate(names):
            title = titles[i] if i < len(titles) else ""

            submission.coauthor_rows.append({
                "display_name": f"{title} {name}".strip(),
            })

        topic_ids = [
            topic.id
            for topic in [submission.topic, submission.secondary_topic]
            if topic
        ]

        suggested_reviewers = reviewers.filter(
            topics__id__in=topic_ids
        ).distinct() if topic_ids else reviewers.none()

        return render(request, "conferences/assign_papers.html", {
            "conference": conference,
            "submission": submission,
            "suggested_reviewers": suggested_reviewers,
            "all_reviewers": reviewers,
            "assignments": submission.review_assignments.all(),
            "reviewer_deadline_extension_days": REVIEWER_DEADLINE_EXTENSION_DAYS,
        })

    submission_data = []

    for submission in submissions:

        submission.coauthor_rows = []

        names = [
            x.strip()
            for x in (submission.coauthors or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        titles = [
            x.strip()
            for x in (submission.coauthor_titles or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        for i, name in enumerate(names):
            title = titles[i] if i < len(titles) else ""

            submission.coauthor_rows.append({
                "display_name": f"{title} {name}".strip(),
            })

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
        "reviewer_deadline_extension_days": REVIEWER_DEADLINE_EXTENSION_DAYS,
    })

@login_required
def review_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    assignment = ReviewAssignment.objects.filter(
        submission=submission,
        reviewer=request.user,
        role="content_reviewer"
    ).first()

    if not assignment:
        return redirect("/")

    if assignment.invitation_status != "accepted":
        messages.info(
            request,
            "Please accept the review invitation before opening the review form."
        )
        return redirect(
            "review_invitation_response",
            assignment_id=assignment.id
        )

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
            )

            mark_content_review_completed_if_ready(submission)

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

    if submission.status != "paper_revision_completed":
        messages.error(request, "This submission does not have a revised paper waiting for content review.")
        return redirect("submission_result", submission_id=submission.id)

    assignments = ReviewAssignment.objects.filter(
        submission=submission,
        role="content_reviewer",
        invitation_status="accepted",
    ).select_related("reviewer")

    reviewer_count = assignments.values("reviewer_id").distinct().count()

    if reviewer_count < REQUIRED_ACCEPTED_CONTENT_REVIEWERS:
        messages.error(
            request,
            "At least two content reviewers must accept the review invitation before content review can start."
        )
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
        f"Revision files for round {submission.revision_round} have been sent back to {reviewer_count} reviewer(s)."
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

    base_submissions = Submission.objects.filter(conference__in=conferences)

    # Keep status filters accurate even before the page is rendered.
    for submission in base_submissions:
        sync_content_review_start_status(submission)
        mark_content_review_completed_if_ready(submission)

    submissions = Submission.objects.filter(conference__in=conferences)

    if selected_status != "all":
        submissions = submissions.filter(status=selected_status)

    data = []

    for submission in submissions:
        reviews = Review.objects.filter(submission=submission)

        assignments = ReviewAssignment.objects.filter(
            submission=submission,
            role="content_reviewer"
        ).select_related(
            "reviewer",
            "reviewer__profile"
        )

        accepted_reviewer_count = assignments.filter(
            invitation_status="accepted"
        ).values("reviewer_id").distinct().count()

        pending_reviewer_count = assignments.filter(
            invitation_status="pending"
        ).values("reviewer_id").distinct().count()

        declined_reviewer_count = assignments.filter(
            invitation_status="declined"
        ).values("reviewer_id").distinct().count()

        avg_auto_score = reviews.aggregate(Avg("auto_score"))["auto_score__avg"]

        data.append({
            "submission": submission,
            "reviews": reviews,
            "assignments": assignments,
            "review_count": reviews.count(),
            "accept_count": reviews.filter(overall_recommendation="accept").count(),
            "minor_count": reviews.filter(overall_recommendation="minor_revision").count(),
            "major_count": reviews.filter(overall_recommendation="major_revision").count(),
            "reject_count": reviews.filter(overall_recommendation="reject").count(),
            "status": submission.status,
            "status_display": submission.get_status_display(),
            "accepted_reviewer_count": accepted_reviewer_count,
            "pending_reviewer_count": pending_reviewer_count,
            "declined_reviewer_count": declined_reviewer_count,
            "required_reviewer_count": REQUIRED_ACCEPTED_CONTENT_REVIEWERS,
            "avg_score": avg_auto_score,
            "judge_decision": submission.judge_decision,
            "judge_decision_display": submission.get_judge_decision_display()
            if submission.judge_decision else "",
        })

    return render(request, "conferences/judge_dashboard.html", {
        "data": data,
        "selected_status": selected_status,
    })


@login_required
def remove_reviewer_assignment(request, assignment_id):
    assignment = get_object_or_404(
        ReviewAssignment.objects.select_related(
            "submission",
            "submission__conference",
            "reviewer",
            "reviewer__profile",
        ),
        id=assignment_id,
        role="content_reviewer",
    )

    can_manage = ConferenceRole.objects.filter(
        conference=assignment.submission.conference,
        user=request.user,
        role__in=["judge", "manager"],
    ).exists()

    if not can_manage:
        return redirect("/")

    selected_status = request.POST.get("selected_status") or "all"
    valid_status_filters = {"all", *dict(Submission.STATUS_CHOICES).keys()}

    if selected_status not in valid_status_filters:
        selected_status = "all"

    redirect_url = f"{reverse('judge_dashboard')}?status={selected_status}"

    if request.method != "POST":
        return redirect(redirect_url)

    submission = assignment.submission
    reviewer_name = (
        getattr(getattr(assignment.reviewer, "profile", None), "full_name_with_title", "")
        or assignment.reviewer.get_full_name()
        or assignment.reviewer.username
    )

    existing_review = Review.objects.filter(
        submission=submission,
        reviewer=assignment.reviewer,
    ).exists()

    assignment.delete()

    sync_content_review_start_status(submission)
    mark_content_review_completed_if_ready(submission)

    message = f"Reviewer {reviewer_name} was removed from {submission.paper_code or submission.title}."

    if existing_review:
        message += " The submitted review was kept in the system."

    messages.success(request, message)
    return redirect(redirect_url)

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
    ).select_related("submission", "template").order_by("-created_at")

    return render(request, "conferences/email_templates.html", {
        "conference": conference,
        "templates": templates,
        "logs": logs,
        "logs_count": logs.count(),
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
            uploaded_file = request.FILES.get("full_paper_file")
            source_path = None
            anonymized_path = None
            submission = None

            try:
                submitted_title = (form.cleaned_data.get("title") or "").strip()
                submitted_first_author_email = (
                    form.cleaned_data.get("first_author_email") or ""
                ).strip()
                duplicate_cutoff = timezone.now() - timedelta(minutes=10)

                # Protect against accidental double-clicks / repeated browser POSTs.
                # The conference row is locked while we check and create the new
                # submission, so two near-simultaneous requests cannot both create
                # the same paper for the same author.
                with transaction.atomic():
                    locked_conference = Conference.objects.select_for_update().get(
                        pk=conference.pk
                    )

                    recent_duplicate = (
                        Submission.objects
                        .filter(
                            conference=locked_conference,
                            author=request.user,
                            title__iexact=submitted_title,
                            first_author_email__iexact=submitted_first_author_email,
                            created_at__gte=duplicate_cutoff,
                        )
                        .order_by("-created_at")
                        .first()
                    )

                    if recent_duplicate:
                        messages.info(
                            request,
                            "This paper appears to have already been submitted. "
                            "Please check My submissions before trying again."
                        )
                        return redirect("my_submissions")

                    submission = form.save(commit=False)

                    submission.conference = locked_conference
                    submission.author = request.user
                    submission.first_author_title = form.cleaned_data.get("first_author_title")
                    submission.coauthor_titles = form.cleaned_data.get("coauthor_titles", "")
                    if hasattr(submission, "submitted_by"):
                        submission.submitted_by = request.user

                    submission.status = "submitted"

                    # Prevent Django from uploading the raw form file before we generate
                    # the paper code and final file names.
                    submission.full_paper_file = None
                    submission.original_submission_file = None
                    submission.anonymized_paper_file = None

                    conference_code = locked_conference.slug.replace("-", "").upper()[:6]

                    last_submission = (
                        Submission.objects
                        .filter(conference=locked_conference)
                        .exclude(paper_code="")
                        .order_by("-id")
                        .first()
                    )

                    next_number = 1

                    if last_submission and last_submission.paper_code:
                        try:
                            next_number = int(last_submission.paper_code.split("-")[-1]) + 1
                        except Exception:
                            next_number = Submission.objects.filter(
                                conference=locked_conference
                            ).count() + 1

                    while True:
                        generated_code = f"{conference_code}-{next_number:03d}"
                        if not Submission.objects.filter(paper_code=generated_code).exists():
                            break
                        next_number += 1

                    submission.paper_code = generated_code
                    submission.save()

                if uploaded_file:
                    extension = Path(uploaded_file.name).suffix.lower()
                    original_filename = f"{submission.paper_code}_submission_{submission.id}{extension}"

                    try:
                        uploaded_file.seek(0)
                    except Exception:
                        pass
                    submission.full_paper_file.save(
                        original_filename,
                        uploaded_file,
                        save=False,
                    )

                    try:
                        uploaded_file.seek(0)
                    except Exception:
                        pass
                    submission.original_submission_file.save(
                        original_filename,
                        uploaded_file,
                        save=False,
                    )

                    if extension == ".docx":
                        try:
                            uploaded_file.seek(0)
                        except Exception:
                            pass

                        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as source_tmp:
                            for chunk in uploaded_file.chunks():
                                source_tmp.write(chunk)
                            source_path = source_tmp.name

                        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as anonymized_tmp:
                            anonymized_path = anonymized_tmp.name

                        anonymize_docx(source_path, anonymized_path)

                        if (
                            not anonymized_path
                            or not os.path.exists(anonymized_path)
                            or os.path.getsize(anonymized_path) == 0
                        ):
                            raise ValueError("Anonymized DOCX was not created correctly.")

                        with open(anonymized_path, "rb") as anonymized_file:
                            submission.anonymized_paper_file.save(
                                f"{submission.paper_code}_submission_{submission.id}.docx",
                                File(anonymized_file),
                                save=False,
                            )

                    submission.save()

                send_event_email("paper_submitted", submission, request=request)
                send_event_email("coauthor_submission_confirmation", submission, request=request)

                messages.success(request, "Paper submitted successfully.")
                return redirect("my_submissions")

            except Exception as e:
                # If the database row was created but file processing failed before
                # the file fields were saved, remove the incomplete row so the
                # author can submit again normally.
                if submission and not getattr(submission.full_paper_file, "name", ""):
                    submission.delete()

                print("Paper upload/anonymization error:", e)
                messages.error(request, f"Paper upload failed: {e}")

            finally:
                if source_path and os.path.exists(source_path):
                    os.remove(source_path)
                if anonymized_path and os.path.exists(anonymized_path):
                    os.remove(anonymized_path)

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
    ).select_related(
        "conference",
        "topic",
        "secondary_topic"
    ).order_by("-created_at")

    for submission in submissions:
        submission.coauthor_rows = []

        names = [x.strip() for x in (submission.coauthors or "").replace("\n", ";").split(";") if x.strip()]

        titles = [x.strip() for x in (submission.coauthor_titles or "").replace("\n", ";").split(";") if x.strip()]

        affiliations = [x.strip() for x in (submission.coauthor_affiliations or "").replace("\n", ";").split(";") if x.strip()]

        countries = [x.strip() for x in (submission.coauthor_countries or "").replace("\n", ";").split(";") if x.strip()]

        for i, name in enumerate(names):
            title = titles[i] if i < len(titles) else ""
            affiliation = affiliations[i] if i < len(affiliations) else ""
            country = countries[i] if i < len(countries) else ""

            submission.coauthor_rows.append({
                "display_name": f"{title} {name}".strip(),
                "affiliation": affiliation,
                "country": country,
            })

        # Show author feedback only from the content review round that
        # belongs to the latest editor decision. When a revision is requested,
        # revision_round is already increased for the NEXT cycle, so the
        # relevant feedback is from the previous round. For accept/reject/layout
        # decisions, the relevant feedback is from the current revision_round.
        if submission.status == "revision_required":
            feedback_round = max((submission.revision_round or 0) - 1, 0)
        else:
            feedback_round = submission.revision_round or 0

        submission.visible_author_reviews = Review.objects.filter(
            submission=submission,
            review_round=feedback_round,
        ).select_related(
            "reviewer",
            "reviewer__profile",
        ).order_by(
            "reviewer_id",
        )

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
        proposed_deadline, deadline_error = parse_proposed_review_deadline(
            request.POST.get("proposed_deadline"),
            conference,
        )

        if deadline_error:
            messages.error(request, deadline_error)
            return redirect(
                "conference_submissions",
                slug=conference.slug
            )

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
            assignment.due_soon_reminder_sent = False
            assignment.overdue_reminder_sent = False
            assignment.save()

        if created:
            send_event_email(
                "review_invitation",
                submission,
                request=request,
                reviewer=reviewer_role.user,
            )
            messages.success(request, "Reviewer assigned successfully.")
        else:
            messages.info(request, "This reviewer is already assigned to this paper.")

        if sync_content_review_start_status(submission):
            send_event_email(
                "review_initiated",
                submission,
                request=request,
            )

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

    for submission in submissions:
        submission.coauthor_rows = []

        names = [
            x.strip()
            for x in (submission.coauthors or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        titles = [
            x.strip()
            for x in (submission.coauthor_titles or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        for i, name in enumerate(names):
            title = titles[i] if i < len(titles) else ""

            submission.coauthor_rows.append({
                "display_name": f"{title} {name}".strip(),
            })

    reviewers = ConferenceRole.objects.filter(
        conference=conference,
        role="content_reviewer"
    ).select_related(
        "user"
    ).prefetch_related(
        "topics"
    ).order_by(
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

def _replace_submission_file(submission, field_name, uploaded_file, filename):
    """Replace one FileField on a submission without immediately saving the model."""
    current_file = getattr(submission, field_name, None)

    if current_file and getattr(current_file, "name", ""):
        current_file.delete(save=False)

    if uploaded_file:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        getattr(submission, field_name).save(
            filename,
            uploaded_file,
            save=False,
        )
    else:
        setattr(submission, field_name, None)


@login_required
def upload_revision(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    user_email = (request.user.email or "").strip().lower()
    coauthor_emails = []

    if submission.coauthor_emails:
        coauthor_emails = [
            email.strip().lower()
            for email in str(submission.coauthor_emails).replace(";", ",").split(",")
            if email.strip()
        ]

    can_upload_revision = (
        submission.author_id == request.user.id
        or getattr(submission, "submitted_by_id", None) == request.user.id
        or user_email == (getattr(submission, "first_author_email", "") or "").strip().lower()
        or user_email in coauthor_emails
    )

    if not can_upload_revision:
        messages.error(request, "You do not have permission to upload a revision for this submission.")
        return redirect("my_submissions")

    if submission.status not in ["revision_required", "layout_revision_required"]:
        messages.error(request, "This submission is not currently open for revision upload.")
        return redirect("my_submissions")

    is_content_revision = submission.status == "revision_required"

    if request.method == "POST":
        form = RevisionUploadForm(
            request.POST,
            request.FILES,
            content_revision=is_content_revision,
        )

        if form.is_valid():
            uploaded_file = form.cleaned_data["full_paper_file"]
            extension = Path(uploaded_file.name).suffix.lower()

            try:
                if is_content_revision:
                    next_round = submission.revision_round or 1
                    base_filename = f"{submission.paper_code}-r{next_round}"
                    clean_filename = f"{base_filename}-clean{extension}"

                    _replace_submission_file(
                        submission,
                        "revised_paper_file",
                        uploaded_file,
                        clean_filename,
                    )
                    _replace_submission_file(
                        submission,
                        "full_paper_file",
                        uploaded_file,
                        clean_filename,
                    )

                    response_file = form.cleaned_data.get("response_to_reviewers_file")
                    response_extension = Path(response_file.name).suffix.lower() if response_file else ""
                    _replace_submission_file(
                        submission,
                        "revision_response_file",
                        response_file,
                        f"{base_filename}-response-to-reviewers{response_extension}" if response_file else "",
                    )

                    marked_file = form.cleaned_data.get("marked_up_manuscript_file")
                    marked_extension = Path(marked_file.name).suffix.lower() if marked_file else ""
                    _replace_submission_file(
                        submission,
                        "revision_marked_file",
                        marked_file,
                        f"{base_filename}-marked-up{marked_extension}" if marked_file else "",
                    )

                    submission.status = "paper_revision_completed"
                    success_message = (
                        "Revision files uploaded successfully. "
                        "They are now ready for the judge to review and send to reviewers."
                    )

                else:
                    next_round = submission.layout_revision_round or 1
                    filename = f"{submission.paper_code}-layout-r{next_round}{extension}"

                    _replace_submission_file(
                        submission,
                        "layout_revised_paper_file",
                        uploaded_file,
                        filename,
                    )
                    _replace_submission_file(
                        submission,
                        "full_paper_file",
                        uploaded_file,
                        filename,
                    )

                    submission.status = "accepted_for_layout"
                    success_message = "Corrected layout version uploaded successfully. It is now ready for layout review."

                submission.save()

            except Exception as e:
                print("Revision upload error:", e)
                messages.error(request, f"Revision upload failed: {e}")
                return redirect("upload_revision", submission_id=submission.id)

            if submission.status == "paper_revision_completed":
                # Notify judge/manager that the author uploaded revision files.
                # Do NOT notify reviewers here. Reviewers receive the re-review
                # invitation only after the judge clicks the Send button.
                send_event_email("revision_uploaded", submission, request=request)

            elif submission.status == "accepted_for_layout":
                send_event_email("layout_correction_submitted", submission, request=request)

            messages.success(request, success_message)
            return redirect("my_submissions")
    else:
        form = RevisionUploadForm(content_revision=is_content_revision)

    return render(request, "conferences/upload_revision.html", {
        "submission": submission,
        "form": form,
        "is_content_revision": is_content_revision,
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

    for submission in submissions:
        submission.coauthor_rows = []

        coauthor_names = [
            x.strip()
            for x in (submission.coauthors or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        coauthor_titles = [
            x.strip()
            for x in (submission.coauthor_titles or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        coauthor_affiliations = [
            x.strip()
            for x in (submission.coauthor_affiliations or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        coauthor_countries = [
            x.strip()
            for x in (submission.coauthor_countries or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        coauthor_orcids = [
            x.strip()
            for x in (submission.coauthor_orcids or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        coauthor_emails = [
            x.strip()
            for x in (submission.coauthor_emails or "").replace("\n", ";").split(";")
            if x.strip()
        ]

        for i, name in enumerate(coauthor_names):
            submission.coauthor_rows.append({
                "name": name,
                "title": coauthor_titles[i] if i < len(coauthor_titles) else "",
                "affiliation": coauthor_affiliations[i] if i < len(coauthor_affiliations) else "",
                "country": coauthor_countries[i] if i < len(coauthor_countries) else "",
                "orcid": coauthor_orcids[i] if i < len(coauthor_orcids) else "",
                "email": coauthor_emails[i] if i < len(coauthor_emails) else "",
            })

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

    if submission.status not in ["accepted_for_layout", "layout_revision_submitted", "layout_revision_required", "final_accepted"]:
        messages.error(request, "This submission is not currently available for layout review or final file editing.")
        return redirect("layout_dashboard")

    if request.method == "POST":
        form = LayoutDecisionForm(request.POST, request.FILES)

        if form.is_valid():
            status = form.cleaned_data["status"]
            comment = form.cleaned_data["comment"]
            revision_deadline = form.cleaned_data.get("revision_deadline")
            final_publication_file = form.cleaned_data.get("final_publication_file")

            previous_status = submission.status

            submission.status = status
            submission.final_comment = comment

            if final_publication_file:
                extension = Path(final_publication_file.name).suffix.lower()
                filename = f"{submission.paper_code}-final-publication{extension}"

                try:
                    final_publication_file.seek(0)
                except Exception:
                    pass

                submission.final_publication_file.save(
                    filename,
                    final_publication_file,
                    save=False,
                )

            if status == "layout_revision_required":
                submission.layout_revision_message = comment
                submission.layout_revision_round += 1

                if revision_deadline and hasattr(submission, "layout_revision_deadline"):
                    submission.layout_revision_deadline = revision_deadline

            submission.save()

            if status == "layout_revision_required":
                send_event_email("layout_correction_needed", submission, request=request)
            elif status == "final_accepted" and previous_status != "final_accepted":

                decision_reviews_for_email = Review.objects.filter(
                    submission=submission
                ).select_related(
                    "reviewer",
                    "reviewer__profile"
                ).order_by(
                    "review_round",
                    "reviewer_id"
                )

                reviewer_author_comment_lines = []
                visible_reviewer_number = 1

                for review_for_email in decision_reviews_for_email:
                    comment_for_author = (
                        review_for_email.comments_for_authors or ""
                    ).strip()

                    if not comment_for_author:
                        continue

                    reviewer_author_comment_lines.append(
                        f"Reviewer {visible_reviewer_number} "
                        f"(Round {review_for_email.review_round}):\n"
                        f"{comment_for_author}"
                    )

                    visible_reviewer_number += 1

                reviewer_comments_for_authors = "\n\n".join(
                    reviewer_author_comment_lines
                )

                manuscript_accept_extra = {
                    "editor_comments": submission.final_comment or "",
                    "reviewer_comments": reviewer_comments_for_authors,
                }

                send_event_email(
                    "manuscript_accepted",
                    submission,
                    request=request,
                    extra=manuscript_accept_extra,
                )

            if final_publication_file:
                messages.success(request, "Layout decision saved and final print-ready file uploaded successfully.")
            else:
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
def account_settings(request):
    if request.method == "POST":
        form = AccountSettingsForm(request.POST, user=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, "Your account information has been updated successfully.")
            return redirect("account_settings")
    else:
        form = AccountSettingsForm(user=request.user)

    return render(request, "conferences/account_settings.html", {
        "form": form,
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

    if not submission.full_paper_file:
        messages.error(request, "No paper file is available for this submission.")
        return redirect("my_reviews")

    extension = Path(submission.full_paper_file.name).suffix.lower()

    # For non-DOCX files just return current uploaded paper
    if extension != ".docx":
        return redirect(submission.full_paper_file.url)

    source_path = None
    anonymized_path = None

    try:
        # ALWAYS use current full_paper_file
        if hasattr(submission.full_paper_file, "path"):
            source_path = submission.full_paper_file.path
        else:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as source_tmp:
                source_path = source_tmp.name

            urllib.request.urlretrieve(
                submission.full_paper_file.url,
                source_path
            )

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as anonymized_tmp:
            anonymized_path = anonymized_tmp.name

        anonymize_docx(source_path, anonymized_path)

        # overwrite anonymized reviewer file with CURRENT revision
        with open(anonymized_path, "rb") as anonymized_file:
            submission.anonymized_paper_file.save(
                f"{submission.paper_code}-review-round-{submission.revision_round}.docx",
                File(anonymized_file),
                save=False,
            )

        submission.save(update_fields=["anonymized_paper_file", "updated_at"])

        return redirect(submission.anonymized_paper_file.url)

    except Exception as e:
        print("Reviewer paper download/anonymization error:", e)

        messages.error(
            request,
            "Could not prepare the anonymized reviewer file. Please contact the conference manager."
        )

        return redirect("my_reviews")

    finally:
        if (
            source_path
            and os.path.exists(source_path)
            and source_path != getattr(submission.full_paper_file, "path", None)
        ):
            os.remove(source_path)

        if anonymized_path and os.path.exists(anonymized_path):
            os.remove(anonymized_path)



@login_required
def my_reviews(request):
    assignments = ReviewAssignment.objects.filter(
        reviewer=request.user,
        role="content_reviewer",
        submission__status__in=[
            "submitted",
            "reviewer_acceptance_pending",
            "under_review",
            "paper_revision_completed",
            "paper_revision_completed",
            "revision_required",
            "reviews_completed",
        ]
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
        submission__status__in=[
            "submitted",
            "reviewer_acceptance_pending",
            "under_review",
            "revised_submitted",
            "paper_revision_completed",
            "revision_required",
            "reviews_completed",
        ]
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
                role_obj, created = ConferenceRole.objects.get_or_create(
                    conference=conference,
                    user=selected_user,
                    role=role
                )

                # Send email 1 every time reviewer/layout reviewer role is assigned.
                # This gives committee members login instructions and reviewer topics link.
                if role in ["content_reviewer", "layout_reviewer"]:
                    send_conference_role_email(
                        "committee_login_info",
                        conference,
                        selected_user,
                        request=request,
                    )

                if created:
                    messages.success(request, "Conference role assigned successfully.")
                else:
                    messages.info(request, "This user already has that conference role. Login/topics email was sent again.")

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
    ).select_related(
        "user",
        "user__profile"
    ).prefetch_related(
        "topics"
    )

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
    ).select_related("submission", "template").order_by("-created_at")

    failed_logs = logs.filter(status="failed")[:20]

    return render(request, "conferences/email_health_dashboard.html", {
        "conference": conference,
        "status": status,
        "logs": logs,
        "logs_count": logs.count(),
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

@login_required
def reviewer_topics(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    reviewer_role = get_object_or_404(
        ConferenceRole,
        conference=conference,
        user=request.user,
        role="content_reviewer"
    )

    topics = ConferenceTopic.objects.filter(
        conference=conference,
        enabled=True
    ).order_by("order")

    if request.method == "POST":
        selected_topic_ids = request.POST.getlist("topics")
        reviewer_role.topics.set(selected_topic_ids)

        messages.success(request, "Reviewer topics updated successfully.")
        return redirect("reviewer_topics", slug=conference.slug)

    selected_topics = reviewer_role.topics.values_list("id", flat=True)

    return render(request, "conferences/reviewer_topics.html", {
        "conference": conference,
        "topics": topics,
        "selected_topics": selected_topics,
    })
