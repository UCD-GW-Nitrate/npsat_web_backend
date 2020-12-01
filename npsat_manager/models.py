import traceback
import logging
import asyncio
import socket
import json

import numpy

import django
from django.db import models
from django.core.validators import int_list_validator
from django.contrib.auth.models import User

import arrow

from npsat_backend import settings

# Create your models here.

log = logging.getLogger("npsat.manager")


class PercentileAggregate(models.Aggregate):
    """
        I'm pretty sure we aren't using this and I'm just saving it in case we want to adapt it
    """
    function = 'PERCENTILE_CONT'
    name = 'pct'
    output = models.FloatField()
    template = 'percentile_cont(0.5) WITHIN GROUP (ORDER BY year asc)'


class SimpleJSONField(models.TextField):
    """
		converts dicts to JSON strings on save and converts JSON to dicts
		on load
	"""

    def get_prep_value(self, value):
        if type(value) in (str, bytes):
            return value

        return json.dumps(value)

    def from_db_value(self, value, expression, connection):
        return json.loads(value)


class Crop(models.Model):
    # crop types
    SWAT_CROP = 0
    GNLM_CROP = 1
    GENERAL_CROP = 2
    ALL_OTHER_CROPS = 3
    CROP_TYPES = [
        (SWAT_CROP, 'SWAT'),
        (GNLM_CROP, 'GNLM'),
        (GENERAL_CROP, 'BOTH'),
        (ALL_OTHER_CROPS, 'Special identifier of all other crops')
    ]

    name = models.CharField(max_length=255)
    caml_code = models.PositiveSmallIntegerField(null=True, blank=True)
    swat_code = models.PositiveSmallIntegerField(null=True, blank=True)
    crop_type = models.PositiveSmallIntegerField(choices=CROP_TYPES)
    # groups reverse relationship
    similar_crops = models.ManyToManyField("Crop", blank=True, related_name="similar_backward")
    active_in_mantis = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CropGroup(models.Model):
    """
		Crop Groups aggregate crops, such as level 1 and 2
		during Delta ET study. Here, groups are arbitrary,
		and so are the levels. Levels let you find all the groups
		in a certain level so that the groups are themselves
		grouped into a useful unit by which you can find
		all the crops in some grouping scheme
	"""
    crops = models.ManyToManyField(to=Crop, related_name="groups")
    level = models.CharField(max_length=255)


class Region(models.Model):
    """
		Used for the various location models - this will let us have a groupings class
		that can be used for any of the locations
	"""

    # macros for region_type
    CENTRAL_VALLEY = 0
    SUB_BASIN = 1
    CVHM_FARM = 2
    B118_BASIN = 3
    COUNTY = 4
    TOWNSHIPS = 5
    C2V_SIM_SUBREGIONS = 6
    REGION_TYPE = [
        (CENTRAL_VALLEY, "Central Valley"),
        (SUB_BASIN, "Basin"),  # to maintain system integrity: "sub basin" <=> "basin"
        (CVHM_FARM, "CVHMFarm"),
        (B118_BASIN, "b118 basins"),
        (COUNTY, "County"),
        (TOWNSHIPS, "Townships"),
        (C2V_SIM_SUBREGIONS, "C2VsimSubregions")
    ]
    REGION_TYPE_MANTIS = {
        CENTRAL_VALLEY: "CentralValley",
        SUB_BASIN: "Basins",
        COUNTY: "Counties",
        B118_BASIN: "B118",
        TOWNSHIPS: "Townships",
        CVHM_FARM: "CVHMfarms",
        C2V_SIM_SUBREGIONS: "C2VsimSubregions"
    }

    mantis_id = models.CharField(null=True, max_length=255)
    name = models.CharField(max_length=255)
    active_in_mantis = models.BooleanField(default=True)  # Is this region actually ready to be selected?
    geometry = SimpleJSONField(null=True, blank=True)  #
    external_id = models.CharField(null=True, max_length=255, blank=True)
    region_type = models.PositiveSmallIntegerField(choices=REGION_TYPE)  # is it a county, a B118 Basin, etc? we'll need to have some kind of code for this

    def __str__(self):
        return self.name


class Scenario(models.Model):
    """
		scenario table, used during model run creation
	"""
    # macros for scenario type
    TYPE_FLOW = 1
    TYPE_UNSAT = 2
    TYPE_LOAD = 3
    SCENARIO_TYPE = [
        (TYPE_FLOW, "flowScen"),
        (TYPE_UNSAT, "unsatScen"),
        (TYPE_LOAD, "loadScen")
    ]

    # macros for crop used
    GNLM_CROP = 0
    SWAT_CROP = 1
    CROP_CODE_TYPE = [
        (GNLM_CROP, "caml_code"),
        (SWAT_CROP, "swat_code")
    ]

    name = models.CharField(max_length=255, null=False, blank=False)
    active_in_mantis = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)
    scenario_type = models.PositiveSmallIntegerField(choices=SCENARIO_TYPE)
    crop_code_field = models.PositiveSmallIntegerField(choices=CROP_CODE_TYPE, blank=True, null=True)

    def __str__(self):
        return self.name

# class AreaGroup(models.Model):
"""
	Aggregates different areas so they can be referenced together. Won't work as set up - need
	to either refactor entirely or make this use Generic Relations via a manually made
	middle object. See https://docs.djangoproject.com/en/2.0/ref/contrib/contenttypes/#generic-relations
"""


# areas = models.ManyToManyField(to=Area, related_name="area_groups")
# name = models.CharField(max_length=255)


# We should create the following API endpoint to get the percentiles
# /api/percentile/
# {
#	percentiles = [5,15,85,95],
#	model_run = 27
# }

class ModelRun(models.Model):
    """
		The central object for configuring an individual run of the model - is related to modification objects from the
		modification side.
	"""

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['flow_scenario', 'load_scenario', 'unsat_scenario'],
                condition=models.Q(is_base=True),
                name='unique_base_model_scenario'
            ),
        ]

    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)

    # status is used to replace ready, complete, and running
    # status MACRO: 0 - not ready; 1 - ready; 2 - running; 3 - complete; 4 - error
    NOT_READY = 0
    READY = 1
    RUNNING = 2
    COMPLETED = 3
    ERROR = 4
    STATUS_CHOICE = [
        (NOT_READY, 'not ready'),
        (READY, 'ready'),
        (RUNNING, 'running'),
        (COMPLETED, 'completed'),
        (ERROR, 'error'),
    ]
    status = models.IntegerField(default=NOT_READY, choices=STATUS_CHOICE, null=False)

    status_message = models.CharField(max_length=2048, default="", null=True,
                                      blank=True)  # for status info or error messages
    result_values = models.TextField(validators=[int_list_validator], default="", null=True, blank=True)
    date_submitted = models.DateTimeField(default=django.utils.timezone.now, null=True, blank=True)
    date_completed = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="model_runs")

    # global model parameters
    unsaturated_zone_travel_time = models.DecimalField(max_digits=18, decimal_places=8, null=True, blank=True)

    # model will be run on these regions
    regions = models.ManyToManyField(Region, related_name="model_runs")

    # other model specs
    sim_end_year = models.IntegerField(default=2300, blank=True)
    reduction_start_year = models.IntegerField(default=2020, blank=True)
    reduction_end_year = models.IntegerField(default=2025, blank=True)
    water_content = models.DecimalField(max_digits=5, decimal_places=4, default=0)

    # scenarios
    # here we use explicit fields and set a limit to each
    flow_scenario = models.ForeignKey(Scenario, on_delete=models.DO_NOTHING, related_name="model_runs_flow",
                                      limit_choices_to={'scenario_type': Scenario.TYPE_FLOW})
    load_scenario = models.ForeignKey(Scenario, on_delete=models.DO_NOTHING, related_name="model_runs_load",
                                      limit_choices_to={'scenario_type': Scenario.TYPE_LOAD})
    unsat_scenario = models.ForeignKey(Scenario, on_delete=models.DO_NOTHING, related_name="model_runs_unsat",
                                       limit_choices_to={'scenario_type': Scenario.TYPE_UNSAT})

    # resulting metadata from mantis
    n_wells = models.IntegerField(null=True, blank=True)

    # visibility to the public
    public = models.BooleanField(null=False, blank=False, default=False)

    # whether current model is a base model for its scenario
    is_base = models.BooleanField(null=False, blank=False, default=False)

    # modifications - backward relationship

    def load_result(self, values):
        self.result_values = ",".join([str(item) for item in values])
        self.date_run = arrow.utcnow().datetime

    def run(self):
        """
			Runs Mantis and sets the status codes. Saves automatically at the end
		:return:
		"""
        try:
            # TODO: Fix below
            results = None  # mantis.run_mantis(self.modifications.all())
            self.load_result(values=results)
            self.status = self.COMPLETED
            self.status_message = "Successfully run"
        except:
            log.error("Failed to run Mantis. Error was: {}".format(traceback.format_exc()))
            self.status = self.ERROR
            self.status_message = "Model run failed. This error has been reported."

        self.save()

    @property
    def input_message(self):
        msg = f"endSimYear {str(self.sim_end_year)}"
        msg += f" startRed {self.reduction_start_year}"
        msg += f" endRed {self.reduction_end_year}"
        msg += f" flowScen {self.flow_scenario.name}"
        msg += f" loadScen {self.load_scenario.name}"
        msg += f" unsatScen {self.unsat_scenario.name}"
        msg += f" unsatWC {self.water_content}"

        regions = list(self.regions.all())  # coercing to list so I can get the type of the first one - we'll use them all in a moment anyway
        msg += f" bMap {Region.REGION_TYPE_MANTIS[regions[0].region_type]}"
        msg += f" Nregions {len(regions)}"
        for region in regions:
            msg += f" {region.mantis_id}"

        modifications = self.modifications.all()
        crop_code_field = self.load_scenario.get_crop_code_field_display()

        # use a hash map to store all explicit modifications
        explicit_modifications = {}
        for modification in modifications:
            # all other crops
            if modification.crop.crop_type == Crop.ALL_OTHER_CROPS:
                explicit_modifications["All"] = modification.proportion
            # other explicit crop selection
            else:
                explicit_modifications[modification.crop.id] = modification.proportion

        # retrieve all crop within this load scen
        crop_list = [Crop.GENERAL_CROP, ]
        if int(self.load_scenario.crop_code_field) == Scenario.GNLM_CROP:
            crop_list.append(Crop.GNLM_CROP)
        elif int(self.load_scenario.crop_code_field) == Scenario.SWAT_CROP:
            crop_list.append(Crop.SWAT_CROP)

        all_crops_belonged_to_load_scen = Crop.objects.filter(crop_type__in=crop_list)
        msg += f" Ncrops {len(list(all_crops_belonged_to_load_scen))}"

        ### TEMPORARY
        #
        #crop_code_field = "caml_code"
        #
        ### TEMPORARY

        for crop in all_crops_belonged_to_load_scen:
            if crop.id in explicit_modifications:
                msg += f" {int(getattr(crop, crop_code_field))} {explicit_modifications[crop.id]}"
            else:
                msg += f" {getattr(crop, crop_code_field)} {explicit_modifications['All']}"

        msg += " ENDofMSG\n"
        return msg


class ResultPercentile(models.Model):
    model = models.ForeignKey(ModelRun, on_delete=models.CASCADE, related_name="results")
    percentile = models.IntegerField(null=False)
    values = SimpleJSONField()


"""
	def get_results_percentile(self, percentile):
		results_by_year = self.results.aggregate(PercentileAggregate('loading', percentile=percentile, year_field='year'))


class ResultLoading(models.Model):

	model_run = models.ForeignKey(ModelRun, on_delete=models.CASCADE, related_name="results")
	loading = models.FloatField(null=False, blank=False)
	year = models.SmallIntegerField()  # this will be inferred from the order of values coming out of Mantis
	well = models.IntegerField()  # this is just an ID assigned to each stream of values in order coming from Mantis.
									# each well with the same value is *not* the same between model runs, but allows
									# us to group within a model run
"""


class Modification(models.Model):
    class Meta:
        unique_together = ['model_run', 'crop']

    crop = models.ForeignKey(Crop, on_delete=models.DO_NOTHING, related_name="modifications")
    proportion = models.DecimalField(max_digits=5,
                                     decimal_places=4)  # the amount, relative to 2020 of nitrogen applied on these crops - 0 to 1
    # land_area_proportion = models.DecimalField(max_digits=5, decimal_places=4)
    model_run = models.ForeignKey(ModelRun, null=True, blank=True, on_delete=models.CASCADE,
                                  related_name="modifications")


class MantisServer(models.Model):
    """
		We can configure a server pool by instantiating different versions of this model. On startup, a function willl
		trigger each instance to determine if it is online and available, at which point when we go to send out tasks,
		it will be available for use.
	"""

    host = models.CharField(max_length=255)
    port = models.PositiveSmallIntegerField(default=1234)
    online = models.BooleanField(default=False)

    async def get_status(self):
        stream_reader, stream_writer = asyncio.open_connection(self.host, self.port)
        stream_writer.write(settings.MANTIS_STATUS_MESSAGE)
        await stream_writer.drain()

        response = stream_reader.read()  # waits for an "EOF"
        log.debug("Mantis server at {}:{} responded {}".format(self.host, self.port, response))
        if response == settings.MANTIS_STATUS_RESPONSE:
            self.online = True
        else:
            self.online = False
        self.save()

    def startup(self):
        pass

    # self.get_status()  # saves the object once it determines if the server is online

    def send_command(self, model_run: ModelRun):
        """
			Sends commands to MantisServer and loads results back
		:param model_run:
		:return:
		"""
        model_run.status = ModelRun.RUNNING
        model_run.save()

        log.debug("Connecting to server to send command")
        try:
            self._non_async_send(model_run)
        except:
            # on any exception, reset the state of this model run so it will be picked up again later
            model_run.status = ModelRun.READY  # set it to ready on a generic failure so it tries again - we'll set it to error if it tells us to
            model_run.save()
            raise

    def _non_async_send(self, model_run):
        # sanity check: model_run must be attached with at least one region
        if len(model_run.regions.all()) < 1:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        # mantis_reader, mantis_writer = asyncio.open_connection(server.host, server.port)
        # log.debug("Connected successfully")

        command_string = model_run.input_message
        log.info("Command String is: {}".format(command_string))
        s.send(command_string.encode('utf-8'))

        # s.flush()
        # mantis_writer.drain()  # make sure the full command is sent before proceeding with this function

        results = b""
        iter = 0
        while iter < 10000:
            results += s.recv(99999999)  # receive a chunk
            if results.endswith(b"ENDofMSG\n"):  # if Mantis says it finished and closed it, then break - otherwise get another chunk
                break
            if results.startswith(b"0"):
                # Houston, we have a problem - some kind of error message, but it *won't* end with ENDofMSG, so we need to check
                break
            iter += 1
        else:
            log.warning("Waiting for Mantis too many times - it's likely that runs are failing")

        process_results(results, model_run)
        # model_run.result_values = str(results)
        if model_run.status != ModelRun.ERROR:  # if it wasn't already marked as an error
            model_run.status = ModelRun.COMPLETED
            model_run.date_completed = arrow.utcnow().datetime
            model_run.save()

        log.info("Results saved")


def process_results(results, model_run):
    """
		Given the model results,
	:param results:
	:param model_run:
	:return:
	"""
    # This line will only appeared if used provided Test Client
    # status_message = "Client sent hello message\n"
    # if results.startswith(status_message):
    # 	results = results[len(status_message):]  # if it starts with a status message, remove it

    results_values = results.split(b" ")
    if results_values[0] == b"0":  # Yes, a string 0 because of parsing. It means Mantis failed, store the error message
        model_run.status_message = results_values
        log.error(f"Mantis Error: {results}")
        model_run.status = ModelRun.ERROR
        model_run.save()
        return

    # otherwise, Mantis ran, so let's process everything

    # slice off any blanks
    results_values = [value for value in results_values if value not in (
        b"", b"\n")]  # drop any extra empty values we got because they make the total number go off
    model_run.n_wells = int(results_values[1])
    n_years = int(results_values[2])
    results_values = results_values[
                     3:-1]  # first value is status message, second value is number of wells, third is number of years, last is "EndOfMsg"

    # we need to have a number of results divisible by the number of wells and the number of years, so do some checks
    if len(results_values) % n_years != 0 or (len(results_values) / model_run.n_wells) != n_years:
        error_message = "Got an incorrect number of results from model run. Cannot reliably process to percentiles. You may try again"
        model_run.status = ModelRun.ERROR
        model_run.status_message = error_message
        log.error(error_message)  # log it as an error too so it goes to all the appropriate handlers
        return

    # OK, now we should be safe to proceed
    # we're going to make a 2 dimensional numpy array where every row is a well and every column is a year
    # start by making it a numpy array and convert to float by default
    results_array = numpy.array(results_values, dtype=numpy.float)
    results_2d = results_array.reshape(model_run.n_wells, n_years)

    # get the percentiles - when a percentile would be between 2 values, get the nearest actual value in the dataset
    # instead of interpolating between them, mostly because numpy throws errors when we try that.
    # skip all nan in the mantis output
    percentiles = numpy.nanpercentile(results_2d, q=settings.PERCENTILE_CALCULATIONS, interpolation="nearest", axis=0)
    for index, percentile in enumerate(settings.PERCENTILE_CALCULATIONS):
        current_percentiles = json.dumps(
            percentiles[index].tolist())  # coerce from numpy to list, then dump as JSON to a string
        ResultPercentile(model=model_run, percentile=percentile, values=current_percentiles).save()

    model_run.save()
