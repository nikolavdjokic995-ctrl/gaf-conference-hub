from datetime import timedelta

from django.utils import timezone

from .models import Conference, EmailLog, EmailTemplate, Review, ReviewAssignment
from .email_defaults import OFFICIAL_EMAIL_EVENTS
from .emails import send_event_email


def _review_exists_for_assignment(assignment):
    submission = assignment.submission
    current_round = submission.revision_round or 0
    return Review.objects.filter(
        submission=submission,
        reviewer=assignment.reviewer,
        review_round=current_round,
    ).exists()


def _deadline_context(assignment, request=None):
    deadline = assignment.accepted_deadline or assignment.proposed_deadline
    today = timezone.now().date()
    days_left = ""
    if deadline:
        days_left = str((deadline - today).days)
    return {
        "review_deadline": deadline.strftime("%d.%m.%Y.") if deadline else "",
        "accepted_review_deadline": assignment.accepted_deadline.strftime("%d.%m.%Y.") if assignment.accepted_deadline else "",
        "proposed_review_deadline": assignment.proposed_deadline.strftime("%d.%m.%Y.") if assignment.proposed_deadline else "",
        "review_deadline_days": days_left,
        "review_days": days_left,
    }


def process_scheduled_review_emails(conference=None, request=None):
    """
    Sends time-based review emails. Safe to run repeatedly.

    - review_due_soon: 2 days before accepted/proposed deadline
    - review_overdue: after deadline has passed

    It uses ReviewAssignment flags to prevent duplicate sending.
    """
    today = timezone.now().date()
    target_due_date = today + timedelta(days=2)

    assignments = ReviewAssignment.objects.filter(
        role="content_reviewer",
        invitation_status="accepted",
    ).select_related("submission", "submission__conference", "reviewer")

    if conference is not None:
        assignments = assignments.filter(submission__conference=conference)

    result = {
        "due_soon_sent": 0,
        "overdue_sent": 0,
        "skipped": 0,
    }

    for assignment in assignments:
        deadline = assignment.accepted_deadline or assignment.proposed_deadline
        if not deadline:
            result["skipped"] += 1
            continue

        if _review_exists_for_assignment(assignment):
            result["skipped"] += 1
            continue

        extra = _deadline_context(assignment, request=request)

        if deadline == target_due_date and not getattr(assignment, "due_soon_reminder_sent", False):
            sent = send_event_email(
                "review_due_soon",
                assignment.submission,
                request=request,
                reviewer=assignment.reviewer,
                extra=extra,
            )
            if sent:
                assignment.due_soon_reminder_sent = True
                assignment.save(update_fields=["due_soon_reminder_sent"])
                result["due_soon_sent"] += 1
            else:
                result["skipped"] += 1

        if deadline < today and not getattr(assignment, "overdue_reminder_sent", False):
            sent = send_event_email(
                "review_overdue",
                assignment.submission,
                request=request,
                reviewer=assignment.reviewer,
                extra=extra,
            )
            if sent:
                assignment.overdue_reminder_sent = True
                assignment.save(update_fields=["overdue_reminder_sent"])
                result["overdue_sent"] += 1
            else:
                result["skipped"] += 1

    return result


def get_email_workflow_status(conference):
    today = timezone.now().date()
    due_date = today + timedelta(days=2)

    assignments = ReviewAssignment.objects.filter(
        submission__conference=conference,
        role="content_reviewer",
        invitation_status="accepted",
    ).select_related("submission", "reviewer")

    due_soon_pending = []
    overdue_pending = []

    for assignment in assignments:
        deadline = assignment.accepted_deadline or assignment.proposed_deadline
        if not deadline or _review_exists_for_assignment(assignment):
            continue
        if deadline == due_date and not getattr(assignment, "due_soon_reminder_sent", False):
            due_soon_pending.append(assignment)
        if deadline < today and not getattr(assignment, "overdue_reminder_sent", False):
            overdue_pending.append(assignment)

    existing_events = set(
        EmailTemplate.objects.filter(conference=conference).values_list("event", flat=True)
    )
    missing_templates = [event for event in OFFICIAL_EMAIL_EVENTS if event not in existing_events]

    disabled_templates = EmailTemplate.objects.filter(
        conference=conference,
        event__in=OFFICIAL_EMAIL_EVENTS,
        enabled=False,
    ).order_by("event")

    failed_count = EmailLog.objects.filter(conference=conference, status="failed").count()

    return {
        "due_soon_pending": due_soon_pending,
        "overdue_pending": overdue_pending,
        "missing_templates": missing_templates,
        "disabled_templates": disabled_templates,
        "failed_count": failed_count,
        "total_templates": EmailTemplate.objects.filter(conference=conference).count(),
        "sent_count": EmailLog.objects.filter(conference=conference, status="sent").count(),
        "skipped_count": EmailLog.objects.filter(conference=conference, status="skipped").count(),
    }
