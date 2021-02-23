"""
	As opposed to the mantis code that tries to run Mantis in Python (still not fully complete as of this
	writing), this code manages the handoff to a standalone Mantis server that processes requests.
"""

import socket
import asyncio
import logging

from asgiref.sync import sync_to_async, async_to_sync

from npsat_manager import models
from npsat_backend import settings

log = logging.getLogger("npsat.manager.mantis_manager")

LOAD_SLEEP = 1


@sync_to_async
def _get_runs_for_queue():
    new_runs = models.ModelRun.objects.filter(
        status=models.ModelRun.READY
    ).prefetch_related(
        "modifications"
    )  # get runs that aren't complete
    runs = list(new_runs)
    for run in runs:
        run.running = True
        run.save()

    return runs


async def load_runs_to_queue(q: asyncio.Queue) -> None:
    while True:
        runs = await _get_runs_for_queue()
        for run in runs:
            q.put_nowait(run)
            log.info("Added run {} to queue".format(run.pk))

        await asyncio.sleep(LOAD_SLEEP)  # yield time to workers


async def worker_func(server, q: asyncio.Queue) -> None:
    while True:
        model_run = (
            await q.get()
        )  # basically, this function will sleep until there's something to do
        log.info("Processing run {} on worker {}".format(model_run.pk, server.host))
        test(server, model_run)
        q.task_done()


def test(server, model_run):
    """
            Sends commands to MantisServer and loads results back
    :param model_run:
    :return:
    """
    # area = model_run.area
    modifications = model_run.modifications

    # area_type_id = mantis_area_map_id[
    # 	type(area)]  # we key the ids based on the class being used - this is clunky, but efficient
    # area_subitem_id = area.mantis_id if area_type_id > 1 else ""  # make it an empty string for central valley
    number_of_records = len(
        modifications
    )  # len can be slow with Django, but it'll cache the models for us for later

    # log.debug("Connecting to server to send command")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server.host, server.port))
    # mantis_reader, mantis_writer = asyncio.open_connection(server.host, server.port)
    # log.debug("Connected successfully")

    # sent the command to the server
    s.send(b"C2VSIM_99_09")
    s.send(" 1 0")  # .format(area_type_id, area_subitem_id)
    s.send(" {} {}".format(str(number_of_records), settings.ChangeYear))
    for modification in modifications.objects.all():
        s.send(" {} {}".format(modification.crop.caml_code, modification.proportion))
    s.send("\n")

    # s.flush()
    # mantis_writer.drain()  # make sure the full command is sent before proceeding with this function

    results = s.recv(bufsize=999999)  # basically, wait for the EOF signal
    model_run.result_values = results
    model_run.complete = True
    model_run.running = False
    model_run.save()


def initialize():
    # we're assuming we're starting now, so set ModelRuns to not running if they're not complete
    # this helps if the server shut down while running an analysis and makes sure it gets run when it starts up next.
    all_incomplete_runs = models.ModelRun.objects.filter(status=models.ModelRun.RUNNING)
    for run in all_incomplete_runs:
        run.status = models.ModelRun.READY
        run.save()

    # Now figure out which servers are online - go through the MantisServer object's startup sequence
    all_mantis_servers = models.MantisServer.objects.all()
    for server in all_mantis_servers:
        server.startup()

    # get the online servers only
    mantis_servers = models.MantisServer.objects.filter(online=True)
    return list(
        mantis_servers
    )  # evaluate it so we can use these hand off to these objects using async


async def main_model_run_loop(mantis_servers):
    """
    We're going to ignore this now and just use our single Mantis Server - since it'd require refactoring this
    to support Django, or migrating to Celery + Message Broker, let's not at the moment since we don't have a
    reason to believe we'd need it just yet. We can engineer that in without too much difficulty later. For now,
    we already have code that loads run info to a DB and code that can send commands to a Mantis Server. Let's just
    refactor the process_runs code to not be async and ignore this module so that we can process single runs
    at a time.
    """
    # Now we can actually begin the work of passing information
    # start up a new queue
    q = asyncio.Queue()

    # run_loader checks for new ModelRuns in the DB and throws them into the queue that the servers pull from.
    # we could do this without a queue and just have the servers check the DB, but this results in less DB traffic, I think
    run_loader = asyncio.create_task(load_runs_to_queue(q))

    # initialize a set of workers using those servers
    workers = [asyncio.create_task(worker_func(server, q)) for server in mantis_servers]

    await asyncio.gather(run_loader)
    await q.join()  # Implicitly awaits consumers, too
    for worker in workers:
        worker.cancel()
