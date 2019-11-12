from django.shortcuts import render

from rest_framework import viewsets
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from django.contrib.auth.decorators import login_required

from npsat_manager import serializers
from npsat_manager import models


# Create your views here.

class CropViewSet(viewsets.ModelViewSet):
	"""
	API endpoint that allows listing of crops
	"""
	serializer_class = serializers.CropSerializer
	queryset = models.Crop.objects.order_by('name')


class CountyViewSet(viewsets.ModelViewSet):
	"""
		API endpoint that allows listing of Counties
	"""
	serializer_class = serializers.CountySerializer
	queryset = models.County.objects.filter(active_in_mantis=True).order_by('name')


class ModelRunViewSet(viewsets.ModelViewSet):
	"""
	API endpoint that allows listing of Modifications
	"""
	serializer_class = serializers.RunResultSerializer

	def get_queryset(self):
		return models.ModelRun.objects.filter(user=self.request.user).order_by('id')


class ModificationViewSet(viewsets.ModelViewSet):
	"""
	API endpoint that allows listing of Modifications
	"""
	serializer_class = serializers.ModificationSerializer

	def get_queryset(self):
		return models.Modification.objects.filter(model_run__user=self.request.user).order_by('id')
