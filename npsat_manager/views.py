from rest_framework import viewsets, generics, authentication, permissions
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
from rest_framework.exceptions import APIException
from rest_framework.decorators import action

import logging

from npsat_manager import serializers
from npsat_manager import models
from npsat_backend import local_settings
from npsat_manager.support import (
    tokens,
)  # token code makes sure that all users have tokens - needs to be imported somewhere

from django.core.mail import send_mail
from django.conf import settings
from random import randrange
import numpy

from django.http import HttpResponse
from django.db.models import Q, Exists, ExpressionWrapper, F, FloatField, OuterRef

import arrow

from shapely.geometry import Point, Polygon

from joblib import Parallel, delayed

log = logging.getLogger("npsat.manager")

class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system."""
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.UserSerializer

    def post(self, request):
        """Create a new user."""
        request.data["verification_code"] = str(randrange(100000, 999999))
        send_mail(
            "Verify your NPSAT account",
            "Your verification code is: " + request.data["verification_code"],
            settings.EMAIL_HOST_USER,
            [request.data["email"]],
            fail_silently=True,
        )
        return super().post(request)
    
class SendVerificationEmail(generics.UpdateAPIView):
    """Send a verification email to the user."""
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        self.request.user.verification_code = str(randrange(100000, 999999))
        self.request.user.save()

        response = send_mail(
            "Verify your NPSAT account",
            "Your verification code is: " + self.request.user.verification_code,
            settings.EMAIL_HOST_USER,
            [self.request.user.email],
            fail_silently=False,
        )
        return Response({"response": response})
    
class SendUnauthenticatedVerificationEmail(generics.UpdateAPIView):
    """Send a verification email to the user."""
    permission_classes = [permissions.AllowAny]

    def put(self, request):
        users = models.CustomUser.objects.filter(email=request.data["email"])
        if (users.count() == 0):
            raise APIException("User not found")
        
        user = users[0]
        user.verification_code = str(randrange(100000, 999999))
        user.save()

        response = send_mail(
            "Verify your NPSAT account",
            "Your verification code is: " + user.verification_code,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        return Response({"response": response})
    
class VerifyCode(generics.UpdateAPIView):
    """Verify the user's code."""
    permission_classes = [permissions.AllowAny]

    def put(self, request):
        users = models.CustomUser.objects.filter(email=request.data["email"])
        if (users.count() == 0):
            raise APIException("User not found")
        
        user = users[0]

        if (user.verification_code != request.data["verification_code"]):
            raise APIException("Invalid code")
        
        token, created = Token.objects.get_or_create(user=user)
        user.is_verified = 1
        user.save()

        return Response(
            {
                "token": token.key,
                "user_id": user.pk,
                "username": user.username,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "is_verified": user.is_verified,
                "email": user.email,
            }
        )

class CustomAuthToken(ObtainAuthToken):
    """
    Via https://www.django-rest-framework.org/api-guide/authentication/
    Creates a custom object that returns more than just the auth token when users hit the API endpoint.
    """

    def post(self, request, *args, **kwargs):
        serializer_class = serializers.AuthTokenSerializer
        serializer = serializer_class(
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
                "is_verified": user.is_verified,
                "email": user.email,
            }
        )

class SendUserFeedback(generics.UpdateAPIView):
    """Forward feedback from user to admins via email."""
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        admins = models.CustomUser.objects.filter(is_staff=True)
        
        feedback_type = request.data.get('feedback_type')
        message = request.data.get('message')
        email = request.data.get('email')
        name = request.data.get('name')

        if message is None:
            return Response({"error": "Missing params"}, status=400)
        
        if feedback_type is None:
            feedback_type = "Unspecified"
        
        if email is None:
            email = ""
        
        if name is None:
            name = ""

        for admin in admins:
            response = send_mail(
                "User shared their feedback - " + feedback_type,
                (
                    "Feedback Type: " + feedback_type + "\n\nMessage:\n" + message
                    + "\n\nUser Info:\n" + "Name: " + name + "\nEmail: " + email
                ),
                settings.EMAIL_HOST_USER,
                [admin.email],
                fail_silently=False,
            )
        return Response({"response": response})
    
class ManageUserView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""
    serializer_class = serializers.UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Retrieve and return the authenticated user."""
        return self.request.user


class ManageUserPreferenceView(generics.RetrieveUpdateAPIView):
    """Manage the authenticated user."""
    serializer_class = serializers.UserPreferencesSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Retrieve and return the authenticated user."""
        user_preferences, _ = models.UserPreferences.objects.get_or_create(user=self.request.user)
        return user_preferences


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
            is_base=False,
        ).order_by("-date_completed")

        pending_models = models.ModelRun.objects.filter(
            user=self.request.user,
            status__in=[models.ModelRun.READY, models.ModelRun.RUNNING],
            is_base=False,
        ).order_by("-date_submitted")

        all_models = completed_models | pending_models
        pending_model_ids = pending_models.values_list('id', flat=True)

        recent_published_models = (
            models.ModelRun.objects.exclude(user=self.request.user)
            .filter(public=True)
            .filter(is_base=False)
            .order_by("-date_completed")
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
                "recent_models": serializers.RunResultSerializer(
                    all_models, many=True
                ).data,
                "pending_model_ids": pending_model_ids,
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
                
                queue_position = None
                if model.status == models.ModelRun.READY:
                    queue_position = (
                        models.ModelRun.objects.filter(
                            status=models.ModelRun.READY,
                            is_base=False,
                        )
                        .filter(
                            Q(date_submitted__lt=model.date_submitted)
                        )
                        .count()
                        + 1
                    )
                
                results.append(
                    {"name": model.name, "id": int(model_id), "status": model.status, "queue_position": queue_position}
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
    

class WellViewSet(viewsets.ModelViewSet):
    """
    Well information

    Permissions: IsAdminUser | ReadOnly (Admin users can do all operations, others can use HEAD and GET)
    """

    permission_classes = [IsAdminUser | ReadOnly]
    serializer_class = serializers.WellSerializer

    def get_queryset(self):
        queryset = models.Well.objects.all()

        flow_model = self.request.query_params.get("flow_model", False)
        rch_type = self.request.query_params.get("rch_type", False)
        well_type = self.request.query_params.get("well_type", False)
        eid = self.request.query_params.get("eid", False)
        depth_range_min = self.request.query_params.get("depth_range_min", False)
        depth_range_max = self.request.query_params.get("depth_range_max", False)
        unsat_range_min = self.request.query_params.get("unsat_range_min", False)
        unsat_range_max = self.request.query_params.get("unsat_range_max", False)
        basin = self.request.query_params.getlist("basin", False)
        county = self.request.query_params.getlist("county", False)
        b118 = self.request.query_params.getlist("b118", False)
        tship = self.request.query_params.getlist("tship", False)
        subreg = self.request.query_params.getlist("subreg", False)
        min_depth = self.request.query_params.getlist("min_depth", False)
        max_depth = self.request.query_params.getlist("max_depth", False)
        min_unsat = self.request.query_params.getlist("min_unsat", False)
        max_unsat = self.request.query_params.getlist("max_unsat", False)

        if flow_model:
            queryset = queryset.filter(flow_model=flow_model)

        if rch_type:
            queryset = queryset.filter(rch_type=rch_type)

        if well_type:
            queryset = queryset.filter(well_type=well_type)

        if eid:
            queryset = queryset.filter(eid=eid)

        if depth_range_min:
            queryset = queryset.filter(depth__gte=depth_range_min)

        if depth_range_max:
            queryset = queryset.filter(depth__lte=depth_range_max)

        if unsat_range_min:
            queryset = queryset.filter(unsat__gte=unsat_range_min)

        if unsat_range_max:
            queryset = queryset.filter(unsat__lte=unsat_range_max)

        if basin:
            query = Q()
            for b in basin:
                query.add(Q(basin=b), Q.OR)
            queryset = queryset.filter(query)

        if county:
            query = Q()
            for c in county:
                query.add(Q(county=c), Q.OR)
            queryset = queryset.filter(query)

        if b118:
            query = Q()
            for b in b118:
                query.add(Q(b118=b), Q.OR)
            queryset = queryset.filter(query)

        if tship:
            query = Q()
            for t in tship:
                query.add(Q(tship=t), Q.OR)
            queryset = queryset.filter(query)
        
        if subreg:
            query = Q()
            for s in subreg:
                query.add(Q(subreg=s), Q.OR)
            queryset = queryset.filter(query)

        if min_unsat:
            queryset = queryset.order_by('unsat')
            queryset = queryset.filter(Q(id=queryset.first().id))

        if max_unsat:
            queryset = queryset.order_by('unsat')
            queryset = queryset.filter(Q(id=queryset.last().id))

        if min_depth:
            queryset = queryset.order_by('depth')
            queryset = queryset.filter(Q(id=queryset.first().id))

        if max_depth:
            queryset = queryset.order_by('depth')
            queryset = queryset.filter(Q(id=queryset.last().id))

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

    def list(self, response):
        queryset = models.Region.objects.filter(active_in_mantis=True).order_by("name")
        region_type = self.request.query_params.get("region_type", False)

        if region_type:
            queryset = queryset.filter(region_type=region_type)

        regionIds = self.request.query_params.getlist("regionIds", [])
        serializer = None
        if len(regionIds) > 0:
            res = queryset.filter(id__in=regionIds)
            serializer = self.get_serializer(res, many=True)
        else:
            serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]
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
                porosity=instance.porosity,
                depth_range_min=instance.depth_range_min,
                depth_range_max=instance.depth_range_max,
                unsat_range_min=instance.unsat_range_min,
                unsat_range_max=instance.unsat_range_max,
                sim_end_year=instance.sim_end_year,
                mantis_version=instance.mantis_version,
            )


            for region in instance.regions.all():
                base_model = base_model.filter(regions=region)


            if len(base_model) != 0:
                base_model = base_model[0]


        if base_model and include_base:
            serializer = self.get_serializer([instance, base_model], many=True)
        elif not base_model and include_base:
            raise APIException("Base model is not found!")
        else:
            serializer = self.get_serializer(instance, many=True)
        return Response(serializer.data)
    
    def list(self, response):
        modelIds = self.request.query_params.getlist("modelIds", [])
        serializer = None
        if len(modelIds) > 0:
            query_set = models.ModelRun.objects.filter(id__in=modelIds)
            serializer = self.get_serializer(query_set, many=True)
        else:
            serializer = self.get_serializer(models.ModelRun.objects.all(), many=True)
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
    
    def list(self):
        percentileIds = self.request.query_params.getlist("percentileIds", [])
        serializer = None

        if len(percentileIds) > 0:
            query_set = models.ResultPercentile.objects.filter(id__in=percentileIds)
            print(query_set)
            serializer = self.get_serializer(query_set, many=True)
        else:
            serializer = self.get_serializer(models.ResultPercentile.objects.all(), many=True)
        return Response(serializer.data)
    
    # since retrieve() is not defined, retrieve defaults behavior is (1) get_queryset and (2) filter it by id route param


class DynamicPercentileViewSet(viewsets.ReadOnlyModelViewSet):
    # Helper function for dynamic percentile APIs; retrieves the unaggregated,
    # breakthrough curves of wells who meet the depth and geospatial criteria
    def fetch_raw_data(self, raw_simulation_run, depth_range_min, depth_range_max, polygonCoords):
        results_array = numpy.array(raw_simulation_run.values, dtype=float)
        results_2d = results_array.reshape(raw_simulation_run.rows, raw_simulation_run.columns)
        
        # first column of 2d array is well eids
        well_eids = results_2d[:, 0].tolist()

        # fetch wells by eid and filter only the ones that meet the depth criteria
        wells = models.Well.objects.filter(
            eid__in=well_eids,
            depth__gte=depth_range_min,
            depth__lte=depth_range_max
        )

        # filter by user-drawn polygons, don't recount wells if polygons overlap
        if (polygonCoords and len(polygonCoords) > 0):
            seen = set()
            temp_wells = []

            for polyCoords in polygonCoords:
                poly = Polygon([(lng, lat) for lat, lng in polyCoords])

                for w in wells:
                    if w.pk not in seen and poly.contains(Point(w.lon, w.lat)):
                        seen.add(w.pk)
                        temp_wells.append(w)

            wells = temp_wells

        # save eids of filtered wells
        filtered_eid_set = { w.eid for w in wells }

        # save the number breakthrough curves filtered to be able to return
        num_curves = len(filtered_eid_set)
        total_curves = raw_simulation_run.rows

        # create a mask of which rows of the results reference a well which adhere to criteria
        mask = numpy.array([eid in filtered_eid_set for eid in well_eids])

        filtered_results_2d = results_2d[mask, :]
        filtered_results_2d = filtered_results_2d[:, 1:] # remove the well eids from the 2d results
        return (filtered_results_2d, num_curves, total_curves)

    @action(detail=False, methods=['post'])
    def get_dynamic_percentiles(self, request):
        model_id = request.data.get('model_id')
        depth_range_min = request.data.get('depth_range_min')
        depth_range_max = request.data.get('depth_range_max')
        polygonCoords = request.data.get('polygonCoords')
        base_model_id = request.data.get('base_model_id')

        if model_id is None or depth_range_min is None or depth_range_max is None:
            return Response({"error": "Missing params"}, status=400)

        # function to find various percentile curves from raw breakthrough curves,
        # reusable for user-defined model as well as bau
        def get_percentile_map(modelId):  
            query_set = models.RawSimulationRun.objects.filter(
                Q(model_id=modelId)
            )

            raw_simulation_run = query_set.first()

            if raw_simulation_run is None:
                return (None, None, None, None)
            
            expirationDateTime = raw_simulation_run.expiration
            if expirationDateTime < arrow.utcnow().datetime.date():
                raw_simulation_run.delete()
                return (None, None, None, None)
            
            (filtered_results_2d, num_curves, total_curves) = self.fetch_raw_data(
                raw_simulation_run,
                depth_range_min,
                depth_range_max,
                polygonCoords
            )

            # calculate percentiles and format a response
            percentiles = numpy.nanpercentile(
                filtered_results_2d, q=settings.PERCENTILE_CALCULATIONS, interpolation="nearest", axis=0
            )

            percentile_map = {}
            for index, percentile in enumerate(settings.PERCENTILE_CALCULATIONS):
                current_percentiles = percentiles[index].tolist()
                percentile_map[percentile] = current_percentiles
            
            return (percentile_map, expirationDateTime, num_curves, total_curves)
        
        (custom_percentile_map, expirationDateTime, num_curves, total_curves) = get_percentile_map(model_id)
        
        if base_model_id is not None: # user wants to simulataneously fetch bau and custom results
            (base_percentile_map, _, _, _) = get_percentile_map(base_model_id)
        else:
            base_percentile_map = None

        if (custom_percentile_map is None):
            return Response({"error": "No data found"}, status=400)

        return Response({
            "expiration": expirationDateTime.isoformat(),
            "data": custom_percentile_map,
            "base_data": base_percentile_map,
            "num_curves": num_curves,
            "total_curves": total_curves
        })

    # Function to fetch upper-and-lower-bounding confidence curves for specified percentile curves
    @action(detail=False, methods=['post'])
    def get_confidence_interval(self, request):
        model_id = request.data.get('model_id')
        depth_range_min = request.data.get('depth_range_min')
        depth_range_max = request.data.get('depth_range_max')
        polygonCoords = request.data.get('polygonCoords')
        percentiles = request.data.get('percentiles')
        base_model_id = request.data.get('base_model_id')

        if model_id is None or depth_range_min is None or depth_range_max is None or percentiles is None:
            return Response({"error": "Missing params"}, status=400)

        # Get a map of upper and lower confidence curves for each percentile in the request body
        def get_percentile_map(modelId):
            query_set = models.RawSimulationRun.objects.filter(
                Q(model_id=modelId)
            )

            raw_simulation_run = query_set.first()

            if raw_simulation_run is None:
                return None
            
            expirationDateTime = raw_simulation_run.expiration
            if expirationDateTime < arrow.utcnow().datetime.date():
                raw_simulation_run.delete()
                return None
            
            (filtered_results_2d, num_curves, _) = self.fetch_raw_data(
                raw_simulation_run,
                depth_range_min,
                depth_range_max,
                polygonCoords
            )

            def one_bootstrap(seed, percentile):
                numpy.random.seed(seed)
                # resample curves with replacement
                sample_idx = numpy.random.choice(num_curves, size=num_curves, replace=True)
                return numpy.nanpercentile(filtered_results_2d[sample_idx, :], percentile, axis=0)

            nResamples = 100

            percentile_map = {}
            for percentile in percentiles:
                # parallel execution
                bootstrap_percentiles = numpy.array(
                    Parallel(n_jobs=-1)(delayed(one_bootstrap)(s, percentile) for s in range(nResamples))
                )

                # compute confidence interval
                lower = numpy.nanpercentile(bootstrap_percentiles, 2.5, axis=0)
                upper = numpy.nanpercentile(bootstrap_percentiles, 97.5, axis=0)
                
                percentile_map[percentile] = {
                    "lower": lower.tolist(),
                    "upper": upper.tolist(),
                }

            return percentile_map
        
        custom_percentile_map = get_percentile_map(model_id)
        
        if base_model_id is not None: # user wants to simulataneously fetch bau and custom results
            base_percentile_map = get_percentile_map(base_model_id)
        else:
            base_percentile_map = None

        if (custom_percentile_map is None):
            return Response({"error": "No data found"}, status=400)

        return Response({
            "data": custom_percentile_map,
            "base_data": base_percentile_map,
        })

class WellExplorerViewset(viewsets.ReadOnlyModelViewSet):
    @action(detail=False, methods=['post'])
    def well_urf_data(self, request):    
        flow_model = request.data.get("flow_model", False)
        rch_type = request.data.get("rch_type", False)
        well_type = request.data.get("well_type", False)
        eid = request.data.get("eid", False)

        if flow_model is None or rch_type is None or well_type is None or eid is None:
            return Response({"error": "Missing params"}, status=400)
        
        well = models.Well.objects.get(
            flow_model=flow_model,
            rch_type=rch_type,
            well_type=well_type,
            eid=eid,
        )

        urf_data = well.urf_points.all()

        serializer = serializers.URFSerializer(urf_data, many=True)
        return Response(serializer.data)
        
    
    @action(detail=False, methods=['post'])
    def get_wells_by_age_thres(self, request):
        # Filter wells by their associated "urf_points"
        # Only keep wells who have at least ONE urf row
        # which meets the age threshold: 
        # porosity * urf_point.age_a + urf_point.age_b >= agethres 

        flow_model = request.data.get("flow_model")
        rch_type = request.data.get("rch_type")
        well_type = request.data.get("well_type")
        depth_range_min = request.data.get("depth_range_min")
        depth_range_max = request.data.get("depth_range_max")
        
        # Each of the following params will be arrays of region ids
        basin = request.data.get("basin")
        county = request.data.get("county")
        b118 = request.data.get("b118")
        tship = request.data.get("tship")
        subreg = request.data.get("subreg")
        
        # Params to filter by agethres
        porosity = request.data.get("por")
        agethres = request.data.get("agethres")

        wells = models.Well.objects.all()
        if flow_model is None or rch_type is None or well_type is None:
            return Response({"error": "Missing params"}, status=400)
        
        # Apply well attribute filters
        wells = wells.filter(flow_model=flow_model)
        wells = wells.filter(rch_type=rch_type)
        wells = wells.filter(well_type=well_type)

        if depth_range_min:
            wells = wells.filter(depth__gte=depth_range_min)

        if depth_range_max:
            wells = wells.filter(depth__lte=depth_range_max)

        if basin:
            wells = wells.filter(basin__in=basin)
        elif county:
            wells = wells.filter(county__in=county)
        elif b118:
            wells = wells.filter(b118__in=b118)
        elif tship:
            wells = wells.filter(tship__in=tship)
        elif subreg:
            wells = wells.filter(subreg__in=subreg)
        
        if porosity is None or agethres is None:
            serializer = serializers.WellExplorerSerializer(wells, many=True)
            return Response(serializer.data)

        # Filter based on associated urf points
        qualifying_urf = (
            models.URFPoint.objects
            .filter(well_id=OuterRef("pk"))
            .annotate(
                calculated_age=ExpressionWrapper(
                    porosity * F("age_a") + F("age_b"),
                    output_field=FloatField(),
                )
            )
            .filter(
                age_a__isnull=False,
                age_b__isnull=False,
                calculated_age__gt=agethres,
            )
        )
        wells = wells.filter(Exists(qualifying_urf))

        serializer = serializers.WellExplorerSerializer(wells, many=True)
        return Response(serializer.data)
