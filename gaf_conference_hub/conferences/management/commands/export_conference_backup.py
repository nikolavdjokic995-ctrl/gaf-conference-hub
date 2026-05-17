import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder

from conferences.models import Conference, Submission, Review, ReviewAssignment, EmailLog


class Command(BaseCommand):
    help = "Export conference metadata, submissions, reviews, assignments and email logs to a JSON backup file."

    def add_arguments(self, parser):
        parser.add_argument("--slug", required=True, help="Conference slug, e.g. green-building-2026")
        parser.add_argument("--output", default="conference_backup.json", help="Output JSON file path")

    def handle(self, *args, **options):
        slug = options["slug"]
        output = Path(options["output"])

        try:
            conference = Conference.objects.get(slug=slug)
        except Conference.DoesNotExist:
            raise CommandError(f"Conference with slug '{slug}' was not found.")

        submissions = Submission.objects.filter(conference=conference).select_related("author", "topic", "secondary_topic")
        submission_ids = list(submissions.values_list("id", flat=True))

        data = {
            "conference": {
                "id": conference.id,
                "slug": conference.slug,
                "title_en": conference.title_en,
                "start_date": conference.start_date,
                "end_date": conference.end_date,
                "submission_deadline": conference.submission_deadline,
                "review_deadline": conference.review_deadline,
            },
            "submissions": [],
            "review_assignments": [],
            "reviews": [],
            "email_logs": [],
        }

        for submission in submissions:
            data["submissions"].append({
                "id": submission.id,
                "paper_code": submission.paper_code,
                "title": submission.title,
                "abstract": submission.abstract,
                "keywords": submission.keywords,
                "article_type": submission.article_type,
                "first_author": submission.first_author,
                "first_author_email": submission.first_author_email,
                "first_author_country": submission.first_author_country,
                "coauthors": submission.coauthors,
                "coauthor_emails": submission.coauthor_emails,
                "coauthor_countries": submission.coauthor_countries,
                "status": submission.status,
                "created_at": submission.created_at,
                "updated_at": submission.updated_at,
                "full_paper_file": submission.full_paper_file.name if submission.full_paper_file else "",
                "revised_paper_file": submission.revised_paper_file.name if submission.revised_paper_file else "",
                "final_publication_file": submission.final_publication_file.name if submission.final_publication_file else "",
            })

        for assignment in ReviewAssignment.objects.filter(submission_id__in=submission_ids).select_related("reviewer", "submission"):
            data["review_assignments"].append({
                "submission_id": assignment.submission_id,
                "paper_code": assignment.submission.paper_code,
                "reviewer": assignment.reviewer.email or assignment.reviewer.username,
                "role": assignment.role,
                "invitation_status": assignment.invitation_status,
                "proposed_deadline": assignment.proposed_deadline,
                "accepted_deadline": assignment.accepted_deadline,
                "assigned_at": assignment.assigned_at,
            })

        for review in Review.objects.filter(submission_id__in=submission_ids).select_related("reviewer", "submission"):
            data["reviews"].append({
                "submission_id": review.submission_id,
                "paper_code": review.submission.paper_code,
                "reviewer": review.reviewer.email or review.reviewer.username,
                "review_round": review.review_round,
                "overall_recommendation": review.overall_recommendation,
                "auto_score": review.auto_score,
                "comments_for_authors": review.comments_for_authors,
                "comments_for_editors": review.comments_for_editors,
                "created_at": review.created_at,
                "updated_at": review.updated_at,
            })

        for log in EmailLog.objects.filter(conference=conference)[:1000]:
            data["email_logs"].append({
                "event": log.event,
                "recipient": log.recipient,
                "subject": log.subject,
                "status": log.status,
                "message": log.message,
                "created_at": log.created_at,
            })

        output.write_text(json.dumps(data, indent=2, cls=DjangoJSONEncoder), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Backup exported to {output}"))
