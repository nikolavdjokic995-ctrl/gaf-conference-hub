from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone


def run_review_reminders_throttled():
    """Run review reminder checks at most once per day.

    Useful on Render free plan where cron jobs are not available. Call this from
    judge/manager-facing pages; it will send due-soon and overdue emails only
    once because ReviewAssignment has reminder flags.
    """
    today_key = timezone.now().date().isoformat()
    cache_key = "green_building_review_reminders_last_run"

    if cache.get(cache_key) == today_key:
        return False

    call_command("send_review_reminders")
    cache.set(cache_key, today_key, 60 * 60 * 24)
    return True
