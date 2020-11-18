import logging
import time
import datetime
import traceback


from django.core.management.base import BaseCommand, CommandError

from npsat_manager import mantis_manager, models

log = logging.getLogger("npsat.commands.process_runs")


class Command(BaseCommand):
	help = 'Starts the event loop that processes model runs and sends the commands to Mantis'

	def handle(self, *args, **options):
		self.mantis_server = None
		self.last_warning_time = 0

		while self.mantis_server is None:

			mantis_servers = mantis_manager.initialize()
			# asyncio.run(mantis_manager.main_model_run_loop(mantis_servers))  # see note on main_model_run_loop for why we're not using it

			self._waiting_runs = []
			if len(mantis_servers) > 0:
				self.mantis_server = mantis_servers[0]  # leaving in place the infra for multiple servers in the future, but we'll use one for now
			else:
				# warn once a day if run processing isn't happening
				if datetime.datetime.utcnow().timestamp() - 86400 > self.last_warning_time:
					log.warning("No Mantis server available. Mantis run processing not occurring")
					self.last_warning_time = datetime.datetime.utcnow().timestamp()
				time.sleep(60)  # if we don't have a mantis server, sleep for 60 seconds, then try again

		self.process_runs()

	def process_runs(self):
		while True:
			try:
				self._get_runs()

				if len(self._waiting_runs) == 0:  # if we don't have any runs, go to sleep for a few seconds, then check again
					time.sleep(2)
					continue

				for run in self._waiting_runs:
					self.mantis_server.send_command(model_run=run)
			except:
				log.error("Encountered problem running model run - recovering")
				log.error(traceback.format_exc())
				raise

	def _get_runs(self):
		new_runs = models.ModelRun.objects.filter(status=models.ModelRun.READY)\
											.order_by('date_submitted')\
											.prefetch_related('modifications')  # get runs that aren't complete
		self._waiting_runs = new_runs
