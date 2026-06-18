from datetime import timedelta

from django.utils import timezone

from .models import Conference, EmailLog, EmailTemplate, Review, ReviewAssignment
from .email_defaults import OFFICIAL_EMAIL_EVENTS
from .emails import send_event_email

ACTIVE_CONTENT_REVIEW_STATUS = "under_review"
REMINDER_OFFSET_DAYS = 2


def _review_exists_for_assignment(assignment):
    """Return True when this reviewer has already completed the active round.

    Important: reminders must be tied to an *active* content-review cycle.
    After a judge requests author revision, ``submission.revision_round`` is
    increased for the next cycle even though that next review has not started
    yet. Without the status check in the query below, old accepted assignments
    can look unfinished and receive overdue reminders even after the reviewer
    completed the previous round on time.
    """
    submission = assignment.submission
    current_round = submission.revision_round or 0
    return Review.objects.filter(
        submission=submission,
        reviewer=assignment.reviewer,
        review_round=current_round,
    ).exists()


def _review_deadline_for_assignment(assignment):
    return assignment.final_deadline()


def _deadline_context(assignment, request=None):
    deadline = _review_deadline_for_assignment(assignment)
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
        "days_until_due": days_left,
    }


def _active_review_assignments(conference=None):
    assignments = ReviewAssignment.objects.filter(
        role="content_reviewer",
        invitation_status="accepted",
        submission__status=ACTIVE_CONTENT_REVIEW_STATUS,
    ).select_related("submission", "submission__conference", "reviewer")

    if conference is not None:
        assignments = assignments.filter(submission__conference=conference)

    return assignments


def process_scheduled_review_emails(conference=None, request=None):
    """
    Sends time-based review emails. Safe to run repeatedly.

    - review_due_soon: 2 days before the active review deadline
    - review_overdue: 2 or more days after the active review deadline

    Completed reviews and submissions that are not currently under content
    review are skipped. This prevents stale reminders after a reviewer has
    already submitted the review or after the manuscript moved to author
    revision / decision stages.
    """
    today = timezone.now().date()
    due_soon_date = today + timedelta(days=REMINDER_OFFSET_DAYS)
    overdue_threshold_date = today - timedelta(days=REMINDER_OFFSET_DAYS)

    result = {
        "due_soon_sent": 0,
        "overdue_sent": 0,
        "skipped": 0,
    }

    for assignment in _active_review_assignments(conference=conference):
        deadline = _review_deadline_for_assignment(assignment)
        if not deadline:
            result["skipped"] += 1
            continue

        if _review_exists_for_assignment(assignment):
            result["skipped"] += 1
            continue

        extra = _deadline_context(assignment, request=request)

        if deadline == due_soon_date and not getattr(assignment, "due_soon_reminder_sent", False):
            sent = send_event_email(
                "review_due_soon",
                assignment.submission,
                request=request,
                reviewer=assignment.reviewer,
                assignment=assignment,
                extra=extra,
            )
            if sent:
                assignment.due_soon_reminder_sent = True
                assignment.save(update_fields=["due_soon_reminder_sent"])
                result["due_soon_sent"] += 1
            else:
                result["skipped"] += 1

        if deadline <= overdue_threshold_date and not getattr(assignment, "overdue_reminder_sent", False):
            sent = send_event_email(
                "review_overdue",
                assignment.submission,
                request=request,
                reviewer=assignment.reviewer,
                assignment=assignment,
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
    due_soon_date = today + timedelta(days=REMINDER_OFFSET_DAYS)
    overdue_threshold_date = today - timedelta(days=REMINDER_OFFSET_DAYS)

    due_soon_pending = []
    overdue_pending = []

    for assignment in _active_review_assignments(conference=conference):
        deadline = _review_deadline_for_assignment(assignment)
        if not deadline or _review_exists_for_assignment(assignment):
            continue
        if deadline == due_soon_date and not getattr(assignment, "due_soon_reminder_sent", False):
            due_soon_pending.append(assignment)
        if deadline <= overdue_threshold_date and not getattr(assignment, "overdue_reminder_sent", False):
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
