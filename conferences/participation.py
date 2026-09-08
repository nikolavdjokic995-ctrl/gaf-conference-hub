import re

from django.db import transaction

from .models import ConferenceParticipant, SubmissionParticipant


def normalize_email(value):
    return (value or "").strip().lower()


def _split_rows(value):
    """Split legacy parallel author fields while keeping empty rows where possible."""
    if not value:
        return []
    normalized = str(value).replace("\r\n", "\n").replace("\r", "\n")
    if ";" in normalized and "\n" not in normalized:
        parts = normalized.split(";")
    else:
        parts = normalized.split("\n")
    return [part.strip() for part in parts]


def submission_author_payloads(submission):
    """Return first author + co-authors as ordered dictionaries."""
    payloads = [{
        "name": (submission.first_author or "").strip(),
        "title": (submission.first_author_title or "").strip(),
        "affiliation": (submission.first_author_affiliation or "").strip(),
        "email": (submission.first_author_email or "").strip(),
        "is_first_author": True,
    }]

    names = [row for row in _split_rows(submission.coauthors) if row]
    titles = _split_rows(submission.coauthor_titles)
    emails = _split_rows(submission.coauthor_emails)
    affiliations = _split_rows(submission.coauthor_affiliations)

    for index, name in enumerate(names):
        payloads.append({
            "name": name,
            "title": titles[index] if index < len(titles) else "",
            "affiliation": affiliations[index] if index < len(affiliations) else "",
            "email": emails[index] if index < len(emails) else "",
            "is_first_author": False,
        })

    cleaned = []
    seen = set()
    for item in payloads:
        if not (item["name"] or item["email"]):
            continue
        email_key = normalize_email(item["email"])
        if email_key:
            key = ("email", email_key)
        else:
            key = (
                "fallback",
                re.sub(r"\s+", " ", item["name"].strip().lower()),
                re.sub(r"\s+", " ", item["affiliation"].strip().lower()),
            )
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned


@transaction.atomic
def sync_submission_participants(submission):
    """Synchronize normalized conference participants with the submission author list.

    Email is the primary identity key. For legacy authors without an email we keep a
    submission-specific participant record; final-list deduplication then falls back to
    normalized name + affiliation.
    """
    payloads = submission_author_payloads(submission)
    existing_links = {
        link.author_order: link
        for link in SubmissionParticipant.objects.filter(submission=submission).select_related("participant")
    }

    retained_link_ids = []

    for order, payload in enumerate(payloads, start=1):
        email = payload["email"]
        normalized = normalize_email(email)
        existing_link = existing_links.get(order)

        participant = None
        if normalized:
            participant = ConferenceParticipant.objects.filter(
                conference=submission.conference,
                normalized_email=normalized,
            ).first()

        if participant is None and existing_link and not normalized:
            participant = existing_link.participant

        if participant is None:
            participant = ConferenceParticipant.objects.create(
                conference=submission.conference,
                name=payload["name"],
                title=payload["title"],
                affiliation=payload["affiliation"],
                email=email,
                normalized_email=normalized,
            )
        else:
            changed = False
            for field, value in (
                ("name", payload["name"]),
                ("title", payload["title"]),
                ("affiliation", payload["affiliation"]),
                ("email", email),
            ):
                if value and getattr(participant, field) != value:
                    setattr(participant, field, value)
                    changed = True
            if normalized and participant.normalized_email != normalized:
                participant.normalized_email = normalized
                changed = True
            if changed:
                participant.save()

        if existing_link:
            link = existing_link
            changed_fields = []
            if link.participant_id != participant.id:
                link.participant = participant
                changed_fields.append("participant")
            if link.is_first_author != payload["is_first_author"]:
                link.is_first_author = payload["is_first_author"]
                changed_fields.append("is_first_author")
            if changed_fields:
                link.save(update_fields=changed_fields)
        else:
            link = SubmissionParticipant.objects.create(
                submission=submission,
                participant=participant,
                author_order=order,
                is_first_author=payload["is_first_author"],
            )

        retained_link_ids.append(link.id)

    SubmissionParticipant.objects.filter(submission=submission).exclude(id__in=retained_link_ids).delete()

    return list(
        SubmissionParticipant.objects.filter(submission=submission)
        .select_related("participant")
        .order_by("author_order")
    )


def deduplicated_confirmed_participants(conferences):
    """Return confirmed participants once, preferring normalized email for identity."""
    links = (
        SubmissionParticipant.objects.filter(
            submission__conference__in=conferences,
            submission__status="final_accepted",
            confirmed_attendance=True,
        )
        .select_related("participant", "submission", "submission__conference")
        .order_by("participant__name", "participant__email", "submission__paper_code")
    )

    unique = []
    seen = set()
    for link in links:
        participant = link.participant
        email_key = normalize_email(participant.email)
        if email_key:
            key = ("email", email_key)
        else:
            key = (
                "fallback",
                re.sub(r"\s+", " ", (participant.name or "").strip().lower()),
                re.sub(r"\s+", " ", (participant.affiliation or "").strip().lower()),
            )
        if key in seen:
            continue
        seen.add(key)
        unique.append(participant)

    return unique
