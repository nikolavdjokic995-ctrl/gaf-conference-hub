from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.core.mail import send_mail
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from .models import (
    Conference,
    ConferenceRole,
    Submission,
    ReviewAssignment,
    Review,
    EmailTemplate,
    ConferenceInfoCard,
    ConferenceTopic,
    UserProfile,
)

from .forms import (
    ReviewForm,
    ConferenceOverviewForm,
    SubmissionForm,
    ConferenceInfoCardForm,
    ConferenceTopicForm,
    RegisterForm,
)


def home(request):
    conferences = Conference.objects.all()

    is_manager = False
    is_judge = False
    is_reviewer = False

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
    role__in=["content_reviewer", "layout_reviewer"]
).exists()

    return render(request, "conferences/home.html", {
        "conferences": conferences,
        "is_manager": is_manager,
        "is_judge": is_judge,
        "is_reviewer": is_reviewer,
    })


def conference_overview(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    can_submit = request.user.is_authenticated
    is_manager = False
    is_reviewer = False
    is_judge = False

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

    return render(request, "conferences/conference_overview.html", {
        "conference": conference,
        "can_submit": can_submit,
        "is_manager": is_manager,
        "is_reviewer": is_reviewer,
        "is_judge": is_judge,
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
        status = request.POST.get("status")
        comment = request.POST.get("comment")

        submission.status = status
        submission.final_comment = comment
        submission.save()

        send_conference_email(
            submission.conference,
            "decision_made",
            submission.author,
            {
                "title": submission.title,
                "status": submission.get_status_display(),
                "comment": submission.final_comment,
            }
        )

        return redirect("submission_result", submission_id=submission.id)

    return render(request, "conferences/make_decision.html", {
        "submission": submission
    })


@login_required
def assign_papers(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    if not is_manager:
        return redirect("/")

    all_reviewers = ConferenceRole.objects.filter(
        conference=conference,
        role__in=["content_reviewer", "layout_reviewer"]
    ).select_related("user").prefetch_related("topics")

    if request.method == "POST":
        submission = get_object_or_404(
            Submission,
            id=request.POST.get("submission_id"),
            conference=conference
        )

        reviewer_role = get_object_or_404(
            ConferenceRole,
            id=request.POST.get("reviewer_role_id"),
            conference=conference,
            role__in=["content_reviewer", "layout_reviewer"]
        )

        ReviewAssignment.objects.get_or_create(
            submission=submission,
            reviewer=reviewer_role.user,
            role=reviewer_role.role
        )

        submission.status = "under_review"
        submission.save()

        return redirect("assign_papers", slug=conference.slug)

    submissions = Submission.objects.filter(
        conference=conference
    ).select_related("author", "topic").prefetch_related(
        "review_assignments__reviewer"
    ).order_by("-created_at")

    submission_data = []

    for submission in submissions:
        if submission.topic:
            suggested_reviewers = all_reviewers.filter(
                topics=submission.topic
            )
        else:
            suggested_reviewers = all_reviewers.none()

        submission_data.append({
            "submission": submission,
            "suggested_reviewers": suggested_reviewers,
            "all_reviewers": all_reviewers,
            "assignments": submission.review_assignments.all(),
        })

    return render(request, "conferences/assign_papers.html", {
        "conference": conference,
        "submission_data": submission_data,
    })

@login_required
def my_reviews(request):
    assignments = ReviewAssignment.objects.filter(
        reviewer=request.user
    ).select_related("submission", "submission__conference", "submission__topic")

    return render(request, "conferences/my_reviews.html", {
        "assignments": assignments
    })


@login_required
def review_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    assigned = ReviewAssignment.objects.filter(
        submission=submission,
        reviewer=request.user
    ).exists()

    if not assigned:
        return redirect("/")

    existing_review = Review.objects.filter(
        submission=submission,
        reviewer=request.user
    ).first()

    if request.method == "POST":
        if existing_review:
            form = ReviewForm(request.POST, instance=existing_review)
        else:
            form = ReviewForm(request.POST)

        if form.is_valid():
            review = form.save(commit=False)
            review.submission = submission
            review.reviewer = request.user
            review.save()

            return redirect("/my-reviews/")
    else:
        form = ReviewForm(instance=existing_review)

    return render(request, "conferences/review_form.html", {
        "form": form,
        "submission": submission,
    })


@login_required
def submission_result(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    reviews = Review.objects.filter(submission=submission)
    avg_score = reviews.aggregate(Avg("auto_score"))["auto_score__avg"]

    decision = submission.get_status_display()

    return render(request, "conferences/submission_result.html", {
        "submission": submission,
        "reviews": reviews,
        "avg_score": avg_score,
        "decision": decision
    })


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
def submit_paper(request, slug):
    conference = get_object_or_404(Conference, slug=slug)

    if request.method == "POST":
        form = SubmissionForm(request.POST, request.FILES, conference=conference)

        if form.is_valid():
            submission = form.save(commit=False)
            submission.conference = conference
            submission.author = request.user
            submission.save()

            return redirect("my_submissions")
    else:
        form = SubmissionForm(conference=conference)

    return render(request, "conferences/submit.html", {
        "form": form,
        "conference": conference,
    })


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
    is_manager = ConferenceRole.objects.filter(
        conference=conference,
        user=request.user,
        role="manager"
    ).exists()

    return render(request, "conferences/important_information.html", {
        "conference": conference,
        "cards": cards,
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

    return render(request, "conferences/conference_topics.html", {
        "conference": conference,
        "topics": topics,
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
    ).select_related("conference", "topic").order_by("-created_at")

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
        role="reviewer"
    ).first()

    if not reviewer_role:
        return redirect("conference_overview", slug=conference.slug)

    topics = ConferenceTopic.objects.filter(
        conference=conference,
        enabled=True
    ).order_by("order", "code")

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


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            UserProfile.objects.create(
                user=user,
                affiliation=form.cleaned_data["affiliation"]
            )

            login(request, user)

            return redirect("/")
    else:
        form = RegisterForm()

    return render(request, "conferences/register.html", {
        "form": form
    })
@login_required
def reviewer_dashboard(request):
    assignments = ReviewAssignment.objects.filter(
        reviewer=request.user
    ).select_related(
        "submission",
        "submission__conference",
        "submission__topic",
    )

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