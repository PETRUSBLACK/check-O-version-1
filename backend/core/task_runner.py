"""
Running the background tasks from an HTTP request.

Check-O's most important background job cancels unpaid orders once their
30-minute window has passed and returns the stock to the shop. It is not a
timer — the deadline is written on the order, and something has to come along
and act on it. On a laptop that something is `run_tasks --loop` in its own
terminal. In production it has to be something that survives Petrus closing his
laptop.

Why an endpoint rather than a second service:

Check-O is hosted on a free tier that allows one always-on service, and whose
free web service falls asleep after 15 minutes of inactivity with about a minute
to wake up. A free external cron that calls this endpoint every 5 minutes solves
both problems with one thing: the tasks run, and the service never gets the
chance to fall asleep. A second background worker would need a second paid
service, and a cold start would make the first customer of the morning wait a
minute for the shop list.

Security is a shared secret in a header, not a user account: the caller is a cron
service, which has no login and no business having one. With TASK_RUNNER_TOKEN
unset — which is the case on every development machine — the endpoint refuses
every request, so it cannot be left accidentally open.

Safe to call twice. Each task records that it has acted (`vendor_reminder_sent_at`
on an order, `low_stock_notified_at` on a product, a released reservation), so two
overlapping runs do the work once between them rather than twice each.
"""

import logging
import secrets
from datetime import timedelta, timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

LAGOS = dt_timezone(timedelta(hours=1))  # West Africa Time, no daylight saving

TOKEN_HEADER = "X-Task-Token"


def tiers_due_now(now=None) -> dict:
    """
    Which tiers of task are due, for a caller firing every 5 minutes.

    Stateless on purpose: nothing has to be remembered between calls, so it works
    the same whether the caller is a cron service, a management command or a test.
    Frequent tasks run every time; hourly tasks in the first 5 minutes of the
    hour; daily tasks in the first 5 minutes of the day, Lagos time.

    This only holds at a 5-minute cadence. At 1-minute ticks the same window would
    fire the hourly tasks five times an hour, which is why `run_tasks --loop`
    tracks its own last-run times instead of using this.
    """
    moment = (now or timezone.now()).astimezone(LAGOS)
    return {
        "frequent": True,
        "hourly": moment.minute < 5,
        "daily": moment.hour == 0 and moment.minute < 5,
    }


def run_due_tasks(now=None) -> dict:
    """
    Run whatever is due and report what happened.

    Each tier is wrapped separately. A failure in the daily subscription renewal
    must not stop unpaid orders being cancelled — that one is the difference
    between a shop's stock being free to sell and being held by a customer who
    walked away an hour ago.
    """
    import tasks

    due = tiers_due_now(now)
    ran, failed = [], {}

    for tier, runner in (
        ("frequent", tasks.run_all_frequent_tasks),
        ("hourly", tasks.run_all_hourly_tasks),
        ("daily", tasks.run_all_daily_tasks),
    ):
        if not due[tier]:
            continue
        try:
            runner()
            ran.append(tier)
        except Exception as exc:  # noqa: BLE001 — one bad tier must not stop the rest
            failed[tier] = str(exc)
            logger.error("task_tier_failed tier=%s error=%s", tier, exc)

    return {"ran": ran, "failed": failed}


class RunTasksView(APIView):
    """
    POST (or GET) /api/internal/run-tasks/ with the X-Task-Token header.

    GET is accepted as well as POST. It mutates data, so by the book it should be
    POST only — but several free cron services will only issue a GET, and a
    scheduler that cannot reach this endpoint is worse than an impure verb.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # a cron service has no account, and needs none

    @extend_schema(
        tags=["System"],
        summary="Run due background tasks (cron webhook)",
        description=(
            "Called by the scheduler every 5 minutes. Requires the "
            f"`{TOKEN_HEADER}` header to match TASK_RUNNER_TOKEN. Returns 503 when "
            "no token is configured, so the endpoint is closed by default."
        ),
        request=None,
        responses={
            200: OpenApiResponse(description="Which tiers ran, and anything that failed"),
            401: OpenApiResponse(description="Missing or wrong token"),
            503: OpenApiResponse(description="TASK_RUNNER_TOKEN is not configured"),
        },
    )
    def post(self, request):
        expected = getattr(settings, "TASK_RUNNER_TOKEN", "") or ""

        if not expected:
            return Response(
                {"detail": "Task runner is not configured on this server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        supplied = request.headers.get(TOKEN_HEADER, "")
        # Constant-time: a plain == leaks the token one character at a time to
        # anyone patient enough to measure the response.
        if not secrets.compare_digest(supplied, expected):
            logger.warning("task_runner_rejected ip=%s", _caller(request))
            return Response(
                {"detail": "Not authorised."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        outcome = run_due_tasks()
        logger.info(
            "task_runner_ok ran=%s failed=%s",
            ",".join(outcome["ran"]) or "-",
            ",".join(outcome["failed"]) or "-",
        )
        return Response({"status": "ok", **outcome})

    def get(self, request):
        return self.post(request)


def _caller(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
