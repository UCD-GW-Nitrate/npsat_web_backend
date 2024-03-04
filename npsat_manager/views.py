from rest_framework import viewsets
from rest_framework.permissions import (
    BasePermission,
    IsAuthenticated,
    IsAdminUser,
    SAFE_METHODS,
)
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status

import logging

from npsat_manager import serializers
from npsat_manager import models
from npsat_backend import local_settings
from npsat_manager.support import (
    tokens,
)  # token code makes sure that all users have tokens - needs to be imported somewhere

from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth.models import User

log = logging.getLogger("npsat.manager")

class CustomAuthToken(ObtainAuthToken):
    """
    Via https://www.django-rest-framework.org/api-guide/authentication/
    Creates a custom object that returns more than just the auth token when users hit the API endpoint.
    """

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user_id": user.pk,
                "username": user.username,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "email": user.email,
            }
        )


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class ModifyAccessPermission(BasePermission):
    """
    This permission is particularly defined for model run
    """

    def has_object_permission(self, request, view, obj):
        if request.method not in SAFE_METHODS:
            return request.user == obj.user
        return True


# Create your views here.
class FeedOnDashboard(APIView):
    """
    the API endpoint for dashboard

    It will return information for the dashboard
    1. recent 10 completed model by the authenticated user
    2. recent 10 published model not created by the authenticated user
    3. meta info: total number of models created, etc...
    4. updates/notifications
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def get(self, request):
        """
        return the above mentioned information
        """
        completed_models = models.ModelRun.objects.filter(
            user=self.request.user,
            status=models.ModelRun.COMPLETED,
        ).order_by("-date_completed")
        recent_published_models = (
            models.ModelRun.objects.exclude(user=self.request.user)
            .filter(public=True)
            .order_by("-date_completed")[:10]
        )
        total_created_number = models.ModelRun.objects.filter(
            user=self.request.user
        ).count()
        total_completed_number = completed_models.count()
        total_published_number = models.ModelRun.objects.filter(
            public=True, user=self.request.user
        ).count()
        total_public_number = models.ModelRun.objects.filter(public=True).count()

        # plot data
        plot_models_data = (
            models.ModelRun.objects.filter(Q(user=self.request.user) | Q(public=True))
            .filter(status=models.ModelRun.COMPLETED)
            .order_by("-date_submitted")
        )

        # updates information
        return Response(
            {
                "recent_completed_models": serializers.RunResultSerializer(
                    completed_models[:10], many=True
                ).data,
                "recent_published_models": serializers.RunResultSerializer(
                    recent_published_models, many=True
                ).data,
                "total_created_number": total_created_number,
                "total_public_number": total_public_number,
                "total_completed_number": total_completed_number,
                "total_published_number": total_published_number,
                "plot_models_data": serializers.CompletedRunResultWithValuesSerializer(
                    instance=plot_models_data[:20], many=True, percentiles=[50]
                ).data,
            }
        )


class GetModelStatus(APIView):
    """
    the API endpoints for getting model status

    This API endpoint is specially design for only getting model status

    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def get(self, request):
        """
        return a list of model status or a single model status

        Required parameter:
                ids: a string list of model ids. Eg. 1,10,14,25
        Response:
                status: an array of model status
        =======
        If the required parameters are not provided, error code 404 will be returned.

        For detailed model status types, check @class ModelRun: status.
        The additional constant: "Not found" : -1
        """
        MODEL_NOT_FOUND = -1
        model_ids = self.request.query_params.get("ids", False)
        if not model_ids:
            return HttpResponse(status=400)
        else:
            model_ids = model_ids.split(",")
        results = []
        for model_id in model_ids:
            try:
                model = models.ModelRun.objects.get(id=model_id)
                results.append(
                    {"name": model.name, "id": int(model_id), "status": model.status}
                    if model.is_base or model.public or model.user == self.request.user
                    else {
                        "name": model.name,
                        "id": int(model_id),
                        "status": MODEL_NOT_FOUND,
                    }
                )
            except models.ModelRun.DoesNotExist:
                results.append({"id": int(model_id), "status": MODEL_NOT_FOUND})

        return Response({"results": results})


class ScenarioViewSet(viewsets.ModelViewSet):
    """
    scenario name

    Permissions: IsAdminUser | ReadOnly (Admin users can do all operations, others can use HEAD and GET)
    """

    permission_classes = [IsAdminUser | ReadOnly]
    serializer_class = serializers.ScenarioSerializer

    def get_queryset(self):
        queryset = models.Scenario.objects.filter(active_in_mantis=True).order_by(
            "name"
        )
        scenario_type = self.request.query_params.get("scenario_type", False)
        if scenario_type:
            queryset = queryset.filter(scenario_type=scenario_type)
        return queryset


class CropViewSet(viewsets.ModelViewSet):
    """
    Crop Names and Codes

    Permissions: IsAdminUser | ReadOnly (Admin users can do all operations, others can use HEAD and GET)
    """

    permission_classes = [
        IsAdminUser | ReadOnly
    ]  # Admin users can do any operation, others, can read from the API, but not write

    serializer_class = serializers.CropSerializer

    def get_queryset(self):
        queryset = models.Crop.objects.filter(active_in_mantis=True).order_by("name")
        scenario_id = self.request.query_params.get("flow_scenario", False)
        if scenario_id:
            scenario = models.Scenario.objects.get(id=scenario_id)
            crop_type = scenario.crop_code_field
            crop_type_list = [models.Crop.ALL_OTHER_CROPS, models.Crop.GENERAL_CROP]
            if crop_type == models.Scenario.GNLM_CROP:
                crop_type_list.append(models.Crop.GNLM_CROP)
            elif crop_type == models.Scenario.SWAT_CROP:
                crop_type_list.append(models.Crop.SWAT_CROP)
            queryset = queryset.filter(crop_type__in=crop_type_list)
        return queryset


class RegionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows listing of Region

    Permissions: IsAdminUser | ReadOnly (Admin users can do all operations, others can use HEAD and GET)
    """

    permission_classes = [
        IsAdminUser | ReadOnly
    ]  # Admin users can do any operation, others, can read from the API, but not write

    serializer_class = serializers.RegionSerializer

    def get_queryset(self):
        queryset = models.Region.objects.filter(active_in_mantis=True).order_by("name")
        region_type = self.request.query_params.get("region_type", False)
        if region_type:
            queryset = queryset.filter(region_type=region_type)
        return queryset


class ModelRunViewSet(viewsets.ModelViewSet):
    """
    Create, List, and Modify Model Runs

    Permissions: Must be authenticated

    Optional params:
            filter:
                    status: all(default) or a int array joined by comma, this will filter status
            tags:
                    public: true(default), if the user want to include public model
                    isBase: true(default), if the user want to include base model
                    origin: true(default), if the user want to include self-created model
                    scenarios: false(default) ro a int array joined by comma, this will filter scenarios
            search:
                    search: false(default) or string, this will search the model name and desc
            sorter:
                    false(default) or formatted string as `{param},{ascend | descend}`
            includeBase(only on retrieve request):
                    false(default) or true, this will include base model info
    These params are additional filter to sift models to return the model list
    """

    permission_classes = [IsAuthenticated & ModifyAccessPermission]
    http_method_names = ["get", "post", "put", "delete", "head", "options"]
    serializer_class = serializers.RunResultSerializer

    def get_serializer_context(self):
        context = super(ModelRunViewSet, self).get_serializer_context()
        context.update({"user": self.request.user})
        return context

    def retrieve(self, request, *args, **kwargs):
        serializer = None
        instance = self.get_object()
        # check if user have permission reading this model
        if (
            instance.user != self.request.user
            and not instance.public
            and not instance.is_base
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        # whether the client sends note that include base model
        include_base = self.request.query_params.get("includeBase", False)
        base_model = None
        log.info("includes base2")
        log.info(include_base and not instance.is_base)
        if include_base and not instance.is_base:
            context=self.get_serializer_context()
            base_model = models.ModelRun.objects.filter(
                flow_scenario=instance.flow_scenario,
                unsat_scenario=instance.unsat_scenario,
                load_scenario=instance.load_scenario,
                welltype_scenario=instance.welltype_scenario,
                is_base=True,
                public=True,
                #user=User.objects.get(username=local_settings.ADMIN_BOT_USERNAME),
                user=context["user"],# allow current user to compare and delete BAU created by himself
                water_content=instance.water_content,
                depth_range_min=instance.depth_range_min,
                depth_range_max=instance.depth_range_max,
                screen_length_range_min=instance.screen_length_range_min,
                screen_length_range_max=instance.screen_length_range_max,
                sim_end_year=instance.sim_end_year,
            )
            log.info("first filter2")
            if len(base_model) != 0:
                log.info(base_model[0])

            for region in instance.regions.all():
                base_model = base_model.filter(regions=region)

            log.info("second filter2")
            if len(base_model) != 0:
                log.info(base_model)

            if len(base_model) != 0:
                base_model = base_model[0]
        if base_model:
            serializer = self.get_serializer([instance, base_model], many=True)
        else:
            serializer = self.get_serializer([instance, instance], many=True)
        return Response(serializer.data)

    def get_queryset(self):
        # tags
        include_public = self.request.query_params.get("public", "true")
        include_base = self.request.query_params.get("isBase", "true")
        include_origin = self.request.query_params.get("origin", "true")
        # all objects available for user
        # here we are doing a logic like this:
        # as long as the model satisfies any of the true conditions, include it
        # An alternative logic is to exclude the false conditions
        # queryset = models.ModelRun.objects.filter(
        # 	Q(user=self.request.user) | Q(public=True) | Q(isBase=True)
        # )

        # search
        search_text = self.request.query_params.get("search", False)

        # sorters
        sorter = self.request.query_params.get("sorter", False)

        # filter
        status = self.request.query_params.get("status", False)
        scenarios = self.request.query_params.get("scenarios", False)

        query = None
        if include_public == "true":
            query = Q(public=True)
        if include_base == "true":
            query = Q(is_base=True) if not query else query | Q(is_base=True)
        if include_origin == "true":
            query = (
                Q(user=self.request.user)
                if not query
                else query | Q(user=self.request.user)
            )

        if not query:
            return []
        results = models.ModelRun.objects.filter(query)
        if status:
            results = results.filter(status__in=status.split(","))

        if search_text:
            query = Q(name__contains=search_text) | Q(description__contains=search_text)
            results = results.filter(query)

        if scenarios:
            scenarios_list = scenarios.split(",")
            results = results.filter(
                Q(flow_scenario__in=scenarios_list)
                | Q(unsat_scenario__in=scenarios_list)
                | Q(load_scenario__in=scenarios_list)
                | Q(welltype_scenario__in=scenarios_list)
            )

        if sorter:
            sorter_field, order = sorter.split(",")
            # check if any malicious injection
            if hasattr(models.ModelRun, sorter_field):
                if order == "ascend":
                    return results.order_by(sorter_field)
                else:
                    return results.order_by("-" + sorter_field)

        return results.order_by("-id")


class ModificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows listing of Modifications

    Permissions: Must be authenticated
    """

    permission_classes = [IsAuthenticated]

    serializer_class = serializers.ModificationSerializer

    def get_queryset(self):
        return models.Modification.objects.filter(
            Q(model__user=self.request.user)
            | Q(model__public=True)
            | Q(model__is_base=True)
        ).order_by("-id")


class ResultPercentileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for model results
    restricted to only allow GET request

    Permission: same as the model run, must be authenticated
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    serializer_class = serializers.ResultPercentileSerializer

    def get_queryset(self):
        return models.ResultPercentile.objects.filter(
            Q(model__user=self.request.user)
            | Q(model__public=True)
            | Q(model__is_base=True)
        ).order_by("-id")
