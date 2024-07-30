"""URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path

from rest_framework import routers
from npsat_manager import views

from rest_framework import permissions
from rest_framework.schemas import get_schema_view as drf_get_schema_view

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

# from drf_yasg.views import get_schema_view
# from drf_yasg import openapi

# schema_view = get_schema_view(
#   openapi.Info(
#      title="NPSAT/Mantis API",
#      default_version='v1',
#      description="Test description",
#      terms_of_service="ToDo! ",
#      contact=openapi.Contact(email="contact@snippets.local"),
#      license=openapi.License(name="MIT License"),
#   ),
#   public=True,
#   permission_classes=(permissions.IsAuthenticatedOrReadOnly,),
# )

# set up DRF
router = routers.DefaultRouter()
router.register(r"crop", views.CropViewSet, basename="Crop")
router.register(r"region", views.RegionViewSet, basename="Region")
router.register(r"model_run", views.ModelRunViewSet, basename="ModelRun")
router.register(r"modification", views.ModificationViewSet, basename="Modification")
router.register(r"scenario", views.ScenarioViewSet, basename="Scenario")
router.register(
    r"model_result", views.ResultPercentileViewSet, basename="ResultPercentile"
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/token/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    re_path(r"^api/", include(router.urls)),
    re_path(
        r"^api-token-auth/", views.CustomAuthToken.as_view()
    ),  # POST a username and password here, get a token back
    re_path(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # dashboard feed
    re_path(r"^api/feed/", views.FeedOnDashboard.as_view()),
    # model status
    re_path(r"^api/model_run__status/", views.GetModelStatus.as_view()),
    # DRF docs from drf-yasg
    # url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # DRF schema directly from DRF
    path(
        "openapi",
        drf_get_schema_view(
            title="Your Project", description="API for all things …", version="1.0.0"
        ),
        name="openapi-schema",
    ),
]
