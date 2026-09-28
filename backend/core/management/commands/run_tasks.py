"""
Run SmartMall background tasks (defined in backend/tasks.py).

The most important of these cancels unpaid orders once their 30-minute window has
passed and returns the stock. That is not a timer: the deadline is written on the
order, and this command is what comes along and acts on it. If nothing runs this,
an abandoned payment holds a vendor's stock indefinitely.

Two shapes, same work:

    # Development (Windows has no cron) — leave it running in its own terminal
    python manage.py run_tasks --loop

    # Production on Railway — a cron service runs this every 5 minutes and exits
    python manage.py run_tasks --scheduled

    # One-off, by hand
    python manage.py run_tasks --frequent
    python manage.py run_tasks --hourly
    python manage.py run_tasks --daily
    python manage.py run_tasks --all

How the tiers are decided:

  --scheduled is stateless, for a cron firing every 5 minutes. Frequent tasks run
  every time; hourly tasks run in the first 5 minutes of the hour; daily tasks in
  the first 5 minutes of the day, Lagos time. That only holds at a 5-minute cadence
  — at 1-minute ticks the same window would fire the hourly tasks five times.

  --loop therefore does not use the window. It remembers when it last ran each
  tier and runs one when it is due, so any --every value behaves correctly.
"""

import signal
import time
from datetime import timedelta, timezone as dt_timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone

LAGOS = dt_timezone(timedelta(hours=1))  # West Africa Time, no daylight saving

DEFAULT_EVERY_SECONDS = 300
HOURLY_EVERY = timedelta(hours=1)
DAILY_EVERY = timedelta(days=1)


class Command(BaseCommand):
    help = "Run SmartMall background tasks (see --loop for development)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scheduled",
            action="store_true",
            help="Cron mode: run whatever is due now, then exit. For a 5-minute cron.",
        )
        parser.add_argument(
            "--loop",
            action="store_true",
            help="Keep running, doing the work every --every seconds. Ctrl+C to stop.",
        )
        parser.add_argument(
            "--every",
            type=int,
            default=DEFAULT_EVERY_SECONDS,
            help=f"Seconds between runs in --loop mode (default {DEFAULT_EVERY_SECONDS}).",
        )
        parser.add_argument("--frequent", action="store_true", help="Run 5-minute tasks")
        parser.add_argument("--hourly", action="store_true", help="Run hourly tasks")
        parser.add_argument("--daily", action="store_true", help="Run daily tasks")
        parser.add_argument("--all", action="store_true", help="Run all tasks once")

    def handle(self, *args, **options):
        if options["loop"]:
            if options["every"] < 10:
                raise CommandError("--every must be at least 10 seconds.")
            self._run_loop(every=options["every"])
            return

        run_frequent = options["frequent"] or options["all"]
        run_hourly = options["hourly"] or options["all"]
        run_daily = options["daily"] or options["all"]

        if options["scheduled"]:
            # Stateless, and correct for a cron firing every 5 minutes.
            now = timezone.now().astimezone(LAGOS)
            run_frequent = True
            run_hourly = run_hourly or now.minute < 5
            run_daily = run_daily or (now.hour == 0 and now.minute < 5)

        if not any([run_frequent, run_hourly, run_daily]):
            self.stdout.write(
                self.style.WARNING(
                    "No tasks selected. Use --loop, --scheduled, --frequent, --hourly, "
                    "--daily or --all"
                )
            )
            return

        self._run_once(frequent=run_frequent, hourly=run_hourly, daily=run_daily)
        self.stdout.write(self.style.SUCCESS("Tasks complete."))

    # ─── Looping ──────────────────────────────────────────────────────────────

    def _run_loop(self, *, every: int) -> None:
        stopping = {"now": False}

        def stop(signum, _frame):
            # Railway sends SIGTERM on redeploy; Ctrl+C sends SIGINT. Finish the
            # tick in hand and leave cleanly rather than dying mid-task.
            stopping["now"] = True
            self.stdout.write("\nFinishing this round, then stopping...")

        signal.signal(signal.SIGINT, stop)
        try:
            signal.signal(signal.SIGTERM, stop)
        except (AttributeError, ValueError):
            pass  # not available on every platform / thread

        self.stdout.write(
            self.style.SUCCESS(
                f"Running background tasks every {every} seconds. Press Ctrl+C to stop.\n"
                "Leave this window open — unpaid orders are only cancelled while this runs."
            )
        )

        last_hourly = None
        last_daily = None

        while not stopping["now"]:
            started = time.monotonic()
            now = timezone.now()
            due_hourly = last_hourly is None or now - last_hourly >= HOURLY_EVERY
            due_daily = last_daily is None or now - last_daily >= DAILY_EVERY

            stamp = now.astimezone(LAGOS).strftime("%H:%M:%S")
            try:
                # A long-lived loop must not sit on a connection that the database
                # has since dropped.
                close_old_connections()
                self._run_once(frequent=True, hourly=due_hourly, daily=due_daily, prefix=stamp)
                if due_hourly:
                    last_hourly = now
                if due_daily:
                    last_daily = now
            except Exception as exc:  # noqa: BLE001 — one bad round must not end the loop
                self.stderr.write(self.style.ERROR(f"[{stamp}] round failed: {exc}"))

            if stopping["now"]:
                break

            # Sleep the remainder, so a slow round doesn't push the schedule out.
            # Wake often enough that Ctrl+C feels immediate.
            remaining = every - (time.monotonic() - started)
            while remaining > 0 and not stopping["now"]:
                time.sleep(min(1.0, remaining))
                remaining -= 1.0

        self.stdout.write(self.style.SUCCESS("Stopped."))

    # ─── One round ────────────────────────────────────────────────────────────

    def _run_once(self, *, frequent: bool, hourly: bool, daily: bool, prefix: str = "") -> None:
        import tasks

        tag = f"[{prefix}] " if prefix else ""
        if frequent:
            self.stdout.write(f"{tag}Running frequent tasks...")
            tasks.run_all_frequent_tasks()
        if hourly:
            self.stdout.write(f"{tag}Running hourly tasks...")
            tasks.run_all_hourly_tasks()
        if daily:
            self.stdout.write(f"{tag}Running daily tasks...")
            tasks.run_all_daily_tasks()
