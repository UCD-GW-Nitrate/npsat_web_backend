import logging
from django.utils import timezone


from django.core.management.base import BaseCommand

from npsat_manager import models

log = logging.getLogger("npsat_manager.commands.process_runs")


class Command(BaseCommand):
    help = "Clears raw-simulation-results to save storage"

    def handle(self, *args, **options):
        today = timezone.now().date()

        expired_results = models.RawSimulationRun.objects.filter(expiration__lt=today)

        count = expired_results.count()
        expired_results.delete()

        self.stdout.write(f"Deleted {count} expired models")
