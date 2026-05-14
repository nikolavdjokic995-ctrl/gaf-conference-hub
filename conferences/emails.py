import re

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template import Context, Template
from django.urls import reverse

from .models import ConferenceRole, EmailLog, EmailTemplate


def split_people(value):
    if not value:
        return []
    return [part.strip() for part in re.split(r"[\n,;]+", value) if part.strip()]


def split_emails(value):
    if not value:
        return []
    emails = [part.strip() for part in re.split(r"[\n,;\s]+", value) if part.strip()]
    clean = []
    for email in emails:
        if "@" in email and email not in clean:
            clean.append(email)
    return clean


def user_full_name(user):
    if not user:
        return ""
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.username


def absolute_url(request, name, *args, **kwargs):
    try:
        path = reverse(name, args=args, kwargs=kwargs)
        if request:
            return request.build_absolute_uri(path)
        return path
    except Exception:
        return ""


def build_email_context(submission=None, reviewer=None, request=None, extra=None):
    conference = submission.conference if submission else None
    first_author = submission.first_author if submission else ""
    first_author_email = submission.first_author_email if submission else ""
    coauthors = split_people(submission.coauthors) if submission else []
    coauthor_emails = split_emails(submission.coauthor_emails) if submission else []

    submitting_author_name = user_full_name(submission.author) if submission else ""
    submitting_author_email = submission.author.email if submission and submission.author else ""
    all_authors = [first_author or submitting_author_name] + coauthors
    all_authors = [name for name in all_authors if name]
    all_author_emails = [first_author_email or submitting_author_email] + coauthor_emails
    all_author_emails = [email for email in all_author_emails if email]

    article_type = getattr(submission, "article_type", "") if submission else ""
    if not article_type:
        article_type = "Research paper"

    context = {
        "conference_name": conference.title_en if conference else "",
        "conference_location": conference.location if conference else "",
        "conference_dates": f"{conference.start_date} — {conference.end_date}" if conference else "",
        "conference_contact_email": conference.contact_email if conference else "",
        "paper_title": submission.title if submission else "",
        "submission_id": submission.id if submission else "",
        "paper_code": submission.paper_code if submission else "",
        "submission_status": submission.get_status_display() if submission else "",
        "submitting_author_name": submitting_author_name,
        "submitting_author_email": submitting_author_email,
        "author_name": first_author or submitting_author_name,
        "author_email": first_author_email or submitting_author_email,
        "first_author": first_author,
        "first_author_email": first_author_email,
        "coauthors": ", ".join(coauthors),
        "coauthor_emails": ", ".join(coauthor_emails),
        "all_authors": ", ".join(all_authors),
        "all_author_emails": ", ".join(all_author_emails),
        "reviewer_name": user_full_name(reviewer) if reviewer else "",
        "reviewer_email": reviewer.email if reviewer else "",
        "revision_message": submission.judge_revision_message if submission else "",
        "layout_revision_message": submission.layout_revision_message if submission else "",
        "final_comment": submission.final_comment if submission else "",
        "upload_revision_link": absolute_url(request, "upload_revision", submission.id) if submission else "",
        "submission_result_link": absolute_url(request, "submission_result", submission.id) if submission else "",
        "review_link": absolute_url(request, "review_submission", submission.id) if submission else "",
        "layout_decision_link": absolute_url(request, "layout_decision", submission.id) if submission else "",
        "conference_link": absolute_url(request, "conference_overview", conference.slug) if conference else "",
        "article_type": article_type,
        "abstract": submission.abstract if submission else "",
        "keywords": submission.keywords if submission else "",
        "submitted_on": submission.created_at.strftime("%d.%m.%Y.") if submission and submission.created_at else "",
        "review_deadline": conference.review_deadline.strftime("%d.%m.%Y.") if conference and conference.review_deadline else "",
        "review_days": "10",
        "days_until_due": "2",
        "date_agreed": "",
        "editor_decision": submission.get_status_display() if submission else "",
        "editor_comments": submission.final_comment if submission else "",
        "reviewer_comments": "",
        "revision_deadline": "",
        "layout_deadline": "",
        "temporary_password": "",
    }
    if extra:
        context.update(extra)
    return context


def render_template_text(text, context):
    return Template(text or "").render(Context(context))


def recipients_for_template(template, submission=None, reviewer=None):
    recipients = []
    if submission:
        if template.send_to_author:
            if getattr(submission, "first_author_email", ""):
                recipients.append(submission.first_author_email)
            elif submission.author and submission.author.email:
                recipients.append(submission.author.email)
        if template.send_to_coauthors:
            recipients.extend(split_emails(submission.coauthor_emails))

        conference = submission.conference
        if template.send_to_managers:
            recipients.extend(
                ConferenceRole.objects.filter(
                    conference=conference,
                    role="manager",
                    user__email__gt=""
                ).values_list("user__email", flat=True)
            )
        if template.send_to_layout_reviewers:
            recipients.extend(
                ConferenceRole.objects.filter(
                    conference=conference,
                    role="layout_reviewer",
                    user__email__gt=""
                ).values_list("user__email", flat=True)
            )
    if reviewer and template.send_to_reviewer and reviewer.email:
        recipients.append(reviewer.email)

    clean = []
    for email in recipients:
        if email and email not in clean:
            clean.append(email)
    return clean


def send_event_email(event, submission, request=None, reviewer=None, extra=None):
    template = EmailTemplate.objects.filter(
        conference=submission.conference,
        event=event,
    ).first()

    if template is None:
        EmailLog.objects.create(
            conference=submission.conference,
            submission=submission,
            event=event,
            status="skipped",
            message="No email template exists for this event.",
        )
        return []

    if not template.enabled:
        EmailLog.objects.create(
            conference=submission.conference,
            submission=submission,
            template=template,
            event=event,
            status="skipped",
            message="Template is disabled.",
        )
        return []

    context = build_email_context(submission=submission, reviewer=reviewer, request=request, extra=extra)
    subject = render_template_text(template.subject, context).strip()
    body = render_template_text(template.body, context).strip()
    recipients = recipients_for_template(template, submission=submission, reviewer=reviewer)

    if not recipients:
        EmailLog.objects.create(
            conference=submission.conference,
            submission=submission,
            template=template,
            event=event,
            subject=subject,
            status="skipped",
            message="No recipients were found.",
        )
        return []

    sent = []
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    for recipient in recipients:
        try:
            send_mail(subject, body, from_email, [recipient], fail_silently=False)
            EmailLog.objects.create(
                conference=submission.conference,
                submission=submission,
                template=template,
                event=event,
                recipient=recipient,
                subject=subject,
                status="sent",
            )
            sent.append(recipient)
        except Exception as exc:
            EmailLog.objects.create(
                conference=submission.conference,
                submission=submission,
                template=template,
                event=event,
                recipient=recipient,
                subject=subject,
                status="failed",
                message=str(exc),
            )
    return sent


def preview_template(template, submission=None, reviewer=None, request=None):
    context = build_email_context(submission=submission, reviewer=reviewer, request=request)
    if not submission:
        context.update({
            "conference_name": template.conference.title_en,
            "conference_location": template.conference.location,
            "conference_dates": f"{template.conference.start_date} — {template.conference.end_date}",
            "paper_title": "Example paper title",
            "submission_id": "1",
            "paper_code": "GBC2026-001",
            "author_name": "Example Author",
            "author_email": "author@example.com",
            "submitting_author_name": "Submitting User",
            "submitting_author_email": "submitter@example.com",
            "first_author": "Example Author",
            "first_author_email": "author@example.com",
            "coauthors": "Coauthor One, Coauthor Two",
            "coauthor_emails": "coauthor1@example.com, coauthor2@example.com",
            "all_authors": "Example Author, Coauthor One, Coauthor Two",
            "all_author_emails": "author@example.com, coauthor1@example.com, coauthor2@example.com",
            "reviewer_name": "Example Reviewer",
            "reviewer_email": "reviewer@example.com",
            "revision_message": "Please revise the paper according to the reviewer comments.",
            "layout_revision_message": "Please correct formatting according to the template.",
            "final_comment": "Final decision note.",
            "upload_revision_link": "https://example.com/upload-revision/",
            "submission_result_link": "https://example.com/submission-result/",
            "review_link": "https://example.com/review/",
            "layout_decision_link": "https://example.com/layout-decision/",
            "conference_link": "https://example.com/conference/",
            "article_type": "Research paper",
            "abstract": "Example abstract text.",
            "keywords": "green building, sustainability",
            "submitted_on": "20.02.2026.",
            "review_deadline": "18.04.2026.",
            "review_days": "10",
            "days_until_due": "2",
            "date_agreed": "05.04.2026.",
            "editor_decision": "Minor revision",
            "editor_comments": "There are no comments.",
            "reviewer_comments": "Reviewer comments will appear here.",
            "revision_deadline": "01.05.2026.",
            "layout_deadline": "22.03.2026.",
            "temporary_password": "temporary-password",
        })
    return {
        "subject": render_template_text(template.subject, context).strip(),
        "body": render_template_text(template.body, context).strip(),
        "context": context,
    }
