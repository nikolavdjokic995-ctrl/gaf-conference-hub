from django.db import migrations, models


def recalculate_review_scores(apps, schema_editor):
    Review = apps.get_model("conferences", "Review")

    author_score_map = {
        "yes": 5.0,
        "can_be_improved": 3.5,
        "must_be_improved": 2.0,
    }

    rating_score_map = {
        "high": 5.0,
        "average": 3.5,
        "low": 2.0,
    }

    recommendation_adjustments = {
        "accept": 0.5,
        "minor_revision": -0.2,
        "major_revision": -0.7,
        "reject": -1.5,
    }

    for review in Review.objects.all():
        total = 0.0
        count = 0

        author_fields = [
            review.content_context,
            review.research_design,
            review.arguments_discussion,
            review.results_presented,
            review.references_adequate,
            review.conclusions_supported,
        ]

        for value in author_fields:
            mapped_score = author_score_map.get(value)
            if mapped_score is not None:
                total += mapped_score
                count += 1

        rating_fields = [
            review.originality,
            review.contribution,
            review.structure_clarity,
            review.logical_coherence,
            review.engagement_sources,
            review.overall_merit,
        ]

        for value in rating_fields:
            mapped_score = rating_score_map.get(value)
            if mapped_score is not None:
                total += mapped_score
                count += 1

        score = total / count if count else 3.0

        if review.english_quality == "needs_improvement":
            score -= 0.3

        if review.references_relevant == "no":
            score -= 0.3

        editor_flags = [
            review.conflict_of_interest,
            review.plagiarism_detected,
            review.inappropriate_self_citations,
            review.ethical_concerns,
        ]

        for value in editor_flags:
            if value == "yes":
                score -= 0.8

        score += recommendation_adjustments.get(review.overall_recommendation, 0.0)
        review.auto_score = max(1.0, min(5.0, round(score, 1)))
        review.save(update_fields=["auto_score"])


class Migration(migrations.Migration):

    dependencies = [
        ("conferences", "0025_conferenceinfocard_icon_image_conferencesidebarcard"),
    ]

    operations = [
        migrations.AlterField(
            model_name="review",
            name="auto_score",
            field=models.FloatField(default=3.0),
        ),
        migrations.RunPython(recalculate_review_scores, migrations.RunPython.noop),
    ]
