import logging

from django.core.management.base import BaseCommand

from npsat_manager import load_data

log = logging.getLogger("npsat_manager.commands.process_runs")


class Command(BaseCommand):
    help = "Starts the event loop that processes model runs and sends the commands to Mantis"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mantis_port",
            nargs=1,
            type=int,
            dest="mantis_port",
            default=5941,
        )

    def handle(self, *args, **options):
        if type(options["mantis_port"]) is int:
            port = options["mantis_port"]
        else:
            port = options["mantis_port"][0]

        load_data.load_all(mantis_port_number=port)
