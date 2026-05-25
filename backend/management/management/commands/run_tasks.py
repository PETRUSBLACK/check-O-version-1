"""
Management command to run background tasks manually.
Usage:
    python manage.py run_tasks --hourly
    python manage.py run_tasks --daily
    python manage.py run_tasks --all
"""
import sys
import os

# Add backend dir to path for tasks module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run SmartMall background tasks"

    def add_arguments(self, parser):
        parser.add_argument("--hourly", action="store_true", help="Run hourly tasks")
        parser.add_argument("--daily", action="store_true", help="Run daily tasks")
        parser.add_argument("--all", action="store_true", help="Run all tasks")

    def handle(self, *args, **options):
        from tasks import run_all_hourly_tasks, run_all_daily_tasks

        if options["hourly"] or options["all"]:
            self.stdout.write("Running hourly tasks...")
            run_all_hourly_tasks()
            self.stdout.write(self.style.SUCCESS("Hourly tasks complete."))

        if options["daily"] or options["all"]:
            self.stdout.write("Running daily tasks...")
            run_all_daily_tasks()
            self.stdout.write(self.style.SUCCESS("Daily tasks complete."))

        if not any([options["hourly"], options["daily"], options["all"]]):
            self.stdout.write(self.style.WARNING("No tasks selected. Use --hourly, --daily, or --all"))
