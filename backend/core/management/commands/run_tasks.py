"""
Run SmartMall background tasks (defined in backend/tasks.py).

Usage:
    python manage.py run_tasks --scheduled   # use this for the cron job (every 5 minutes)
    python manage.py run_tasks --frequent    # 5-minute tasks only
    python manage.py run_tasks --hourly
    python manage.py run_tasks --daily
    python manage.py run_tasks --all         # everything, once (handy when testing locally)

--scheduled is designed for ONE cron job running every 5 minutes:
  - frequent tasks run every time
  - hourly tasks run in the first 5 minutes of each hour
  - daily tasks run in the first 5 minutes of the day (midnight Lagos time)
"""
from datetime import timedelta, timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.utils import timezone

LAGOS = dt_timezone(timedelta(hours=1))  # West Africa Time, no daylight saving


class Command(BaseCommand):
    help = "Run SmartMall background tasks"

    def add_arguments(self, parser):
        parser.add_argument("--scheduled", action="store_true", help="Cron mode: run whatever is due now")
        parser.add_argument("--frequent", action="store_true", help="Run 5-minute tasks")
        parser.add_argument("--hourly", action="store_true", help="Run hourly tasks")
        parser.add_argument("--daily", action="store_true", help="Run daily tasks")
        parser.add_argument("--all", action="store_true", help="Run all tasks once")

    def handle(self, *args, **options):
        import tasks

        run_frequent = options["frequent"] or options["all"]
        run_hourly = options["hourly"] or options["all"]
        run_daily = options["daily"] or options["all"]

        if options["scheduled"]:
            now = timezone.now().astimezone(LAGOS)
            run_frequent = True
            run_hourly = run_hourly or now.minute < 5
            run_daily = run_daily or (now.hour == 0 and now.minute < 5)

        if not any([run_frequent, run_hourly, run_daily]):
            self.stdout.write(self.style.WARNING(
                "No tasks selected. Use --scheduled, --frequent, --hourly, --daily or --all"
            ))
            return

        if run_frequent:
            self.stdout.write("Running frequent tasks...")
            tasks.run_all_frequent_tasks()
        if run_hourly:
            self.stdout.write("Running hourly tasks...")
            tasks.run_all_hourly_tasks()
        if run_daily:
            self.stdout.write("Running daily tasks...")
            tasks.run_all_daily_tasks()
        self.stdout.write(self.style.SUCCESS("Tasks complete."))
