from django.core.exceptions import PermissionDenied, ValidationError

from rest_framework import serializers

from npsat_manager import models
from npsat_backend import local_settings
from django.db.models import Q
from django.contrib.auth.models import User


class CropSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Crop
        fields = ("id", "name", "caml_code", "crop_type", "swat_code")


class NestedCropSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Crop
        fields = ("id", "name", "caml_code")
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False,
            },
            "name": {
                "required": False,
            },
            "caml_code": {"required": False},
        }


class RegionSerializer(serializers.ModelSerializer):
    geometry = serializers.JSONField(read_only=True, binary=False)

    class Meta:
        model = models.Region
        fields = ("id", "external_id", "name", "mantis_id", "geometry", "region_type")


class NestedRegionSerializer(
    serializers.ModelSerializer
):  # for use when nested in the model runs to remove geometry
    class Meta:
        model = models.Region
        fields = ("id", "external_id", "name", "mantis_id", "region_type")
        # set id/name/region_type values for POST method
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False,
            },
            "name": {
                "required": False,
            },
            "region_type": {"required": False},
        }


class ScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Scenario
        fields = ("name", "id", "description", "scenario_type")
        extra_kwargs = {
            "id": {
                "read_only": False,
                "required": False,
            },
            "name": {"required": False},
            "description": {"required": False},
            "scenario_type": {"required": False},
        }


class ModificationSerializer(serializers.ModelSerializer):
    # crop = CropSerializer(read_only=True)
    # model_run = RunResultSerializer()

    class Meta:
        model = models.Modification
        fields = ("crop", "proportion", "model_run")

    def validate(self, data):

        # check that the user making this modification actually has permission to attach it to the specified model run.
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            raise PermissionDenied("No User attached to this request - can't modify")

        print(user)
        model_run = data.get("model_run")
        print(model_run)
        print(model_run.user_id)

        if user != model_run.user:
            raise PermissionDenied(
                "You don't have permission to attach modifications to this model run"
            )

        return data


class NestedModificationSerializer(serializers.ModelSerializer):
    crop = NestedCropSerializer(read_only=False)

    class Meta:
        model = models.Modification
        fields = ("id", "crop", "proportion")


class ResultPercentileSerializer(serializers.ModelSerializer):
    values = serializers.JSONField(read_only=True, binary=False)

    class Meta:
        model = models.ResultPercentile
        fields = ("id", "values", "percentile")


class NestedResultPercentileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ResultPercentile
        fields = ("id", "percentile")


class CompletedRunResultWithValuesSerializer(serializers.ModelSerializer):
    def __init__(self, **kwargs):
        self.percentiles = kwargs.pop("percentiles")
        super().__init__(**kwargs)

    results = serializers.SerializerMethodField("get_results")

    def get_results(self, model_run):
        query_set = models.ResultPercentile.objects.filter(
            model=model_run, percentile__in=self.percentiles
        )
        return ResultPercentileSerializer(instance=query_set, many=True).data

    class Meta:
        model = models.ModelRun
        fields = (
            "id",
            "user",
            "name",
            "description",
            "unsaturated_zone_travel_time",
            "date_submitted",
            "date_completed",
            "status",
            "status_message",
            "sim_end_year",
            "water_content",
            "reduction_start_year",
            "reduction_end_year",
            "results",
            "n_wells",
            "public",
            "is_base",
        )


class RunResultSerializer(serializers.ModelSerializer):
    modifications = NestedModificationSerializer(
        many=True, allow_null=True, partial=True
    )
    regions = NestedRegionSerializer(
        many=True, allow_null=True, partial=True, read_only=False
    )
    unsat_scenario = ScenarioSerializer(many=False, read_only=False, allow_null=True)
    load_scenario = ScenarioSerializer(many=False, read_only=False, allow_null=True)
    flow_scenario = ScenarioSerializer(many=False, read_only=False, allow_null=True)
    welltype_scenario = ScenarioSerializer(many=False, read_only=False, allow_null=True)
    results = NestedResultPercentileSerializer(many=True, read_only=True)

    class Meta:
        model = models.ModelRun
        fields = (
            "id",
            "user",
            "name",
            "description",
            "regions",
            "modifications",
            "unsaturated_zone_travel_time",
            "date_submitted",
            "date_completed",
            "status",
            "status_message",
            "sim_end_year",
            "water_content",
            "reduction_start_year",
            "reduction_end_year",
            "is_base",
            "results",
            "n_wells",
            "public",
            "load_scenario",
            "flow_scenario",
            "unsat_scenario",
            "welltype_scenario",
            "applied_simulation_filter",
            "depth_range_min",
            "depth_range_max",
            "screen_length_range_min",
            "screen_length_range_max"
        )
        depth = 0  # should mean that modifications get included in the initial request
        extra_kwargs = {"user": {"required": False}}

    def validate(self, data):
        return data

    def create(self, validated_data):
        user = self.context["user"]
        regions_data = validated_data.pop("regions")
        modifications_data = validated_data.pop("modifications")
        unsat_scenario = validated_data.pop("unsat_scenario")
        load_scenario = validated_data.pop("load_scenario")
        flow_scenario = validated_data.pop("flow_scenario")
        welltype_scenario = validated_data.pop("welltype_scenario")
        water_content = validated_data["water_content"]
        sim_end_year = validated_data["sim_end_year"]
        applied_simulation_filter = validated_data["applied_simulation_filter"]
        depth_range_min = validated_data.get("depth_range_min", None)
        depth_range_max = validated_data.get("depth_range_max", None)
        screen_length_range_min = validated_data.get("screen_length_range_min", None)
        screen_length_range_max = validated_data.get("screen_length_range_max", None)


        # check if there is a BAU created by CURRENT USER
        service_bot = User.objects.get(username=local_settings.ADMIN_BOT_USERNAME)
        BAU_condition = Q()
        BAU_condition &= Q(unsat_scenario__id=unsat_scenario["id"])
        BAU_condition &= Q(flow_scenario__id=flow_scenario["id"])
        BAU_condition &= Q(load_scenario__id=load_scenario["id"])
        BAU_condition &= Q(welltype_scenario__id=welltype_scenario["id"])
        BAU_condition &= Q(is_base=True)
        BAU_condition &= Q(public=True)
        BAU_condition &= Q(user=user)
        BAU_condition &= Q(water_content=water_content)
        BAU_condition &= Q(applied_simulation_filter=applied_simulation_filter)
        if (applied_simulation_filter):
            BAU_condition &= Q(depth_range_min=depth_range_min)
            BAU_condition &= Q(depth_range_max=depth_range_max)
            BAU_condition &= Q(screen_length_range_min=screen_length_range_min)
            BAU_condition &= Q(screen_length_range_max=screen_length_range_max)
        BAU_condition &= Q(sim_end_year=sim_end_year)
        BAU_instances = models.ModelRun.objects.filter(BAU_condition)
        for region in regions_data:
            BAU_instances = BAU_instances.filter(regions__id=region["id"])

        if BAU_instances.count() == 0:
            # create BAU
            if (applied_simulation_filter):
                BAU_model = models.ModelRun.objects.create(
                    #user=service_bot,
                    user=user, #Generate BAU model by current user
                    name="BAU model",  # TODO: generate a better name
                    description="This an automatically generated BAU model. Check model detail page for more information",
                    unsat_scenario=models.Scenario.objects.get(id=unsat_scenario["id"]),
                    flow_scenario=models.Scenario.objects.get(id=flow_scenario["id"]),
                    load_scenario=models.Scenario.objects.get(id=load_scenario["id"]),
                    welltype_scenario=models.Scenario.objects.get(id=welltype_scenario["id"]),
                    is_base=True,
                    public=True,
                    sim_end_year=sim_end_year,
                    reduction_start_year=2020,
                    reduction_end_year=2020,
                    status=models.ModelRun.READY,
                    water_content=water_content,
                    applied_simulation_filter=applied_simulation_filter,
                    depth_range_min=depth_range_min,
                    depth_range_max=depth_range_max,
                    screen_length_range_min=screen_length_range_min,
                    screen_length_range_max=screen_length_range_max,
                )
            else:
                BAU_model = models.ModelRun.objects.create(
                    #user=service_bot,
                    user=user, #Generate BAU model by current user
                    name="BAU model",  # TODO: generate a better name
                    description="This an automatically generated BAU model. Check model detail page for more information",
                    unsat_scenario=models.Scenario.objects.get(id=unsat_scenario["id"]),
                    flow_scenario=models.Scenario.objects.get(id=flow_scenario["id"]),
                    load_scenario=models.Scenario.objects.get(id=load_scenario["id"]),
                    welltype_scenario=models.Scenario.objects.get(id=welltype_scenario["id"]),
                    is_base=True,
                    public=True,
                    sim_end_year=sim_end_year,
                    reduction_start_year=2020,
                    reduction_end_year=2020,
                    status=models.ModelRun.READY,
                    water_content=water_content,
                    applied_simulation_filter=applied_simulation_filter,
                )
            for region in regions_data:
                BAU_model.regions.add(models.Region.objects.get(id=region["id"]))
            models.Modification.objects.create(
                model_run=BAU_model,
                proportion=1,
                crop=models.Crop.objects.get(crop_type=models.Crop.ALL_OTHER_CROPS),
            )
            BAU_model.save()

        model_run = models.ModelRun.objects.create(
            **validated_data,
            user=user,
            unsat_scenario=models.Scenario.objects.get(id=unsat_scenario["id"]),
            flow_scenario=models.Scenario.objects.get(id=flow_scenario["id"]),
            load_scenario=models.Scenario.objects.get(id=load_scenario["id"]),
            welltype_scenario=models.Scenario.objects.get(id=welltype_scenario["id"]),
        )
        for modification in modifications_data:
            proportion = modification["proportion"]
            crop_id = modification["crop"]["id"]
            models.Modification.objects.create(
                model_run=model_run, proportion=proportion, crop_id=crop_id
            )

        # add all other crops if no crops are specified
        if len(modifications_data) == 0:
            models.Modification.objects.create(
                model_run=model_run,
                crop_id=models.Crop.objects.get(
                    crop_type=models.Crop.ALL_OTHER_CROPS
                ).id,
                proportion=1,
            )

        for region in regions_data:
            model_run.regions.add(models.Region.objects.get(id=region["id"]))

        # model is ready to run
        model_run.status = models.ModelRun.READY
        model_run.save()

        return model_run

    def update(self, instance, validated_data):
        """
        currently only allow 'public' to be updated.
        """
        instance.public = validated_data.get("public", instance.public)
        instance.save()
        return instance
