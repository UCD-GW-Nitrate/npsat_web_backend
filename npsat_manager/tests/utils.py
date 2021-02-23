"""
utils file for setting up db and others
====================================================
Note:
    1. this file take a proportion of the actual production files and load these into the test database
    2. this file should be updated when there is a change in the dataset
    3. No teardown method is provided because of the usage of setUpTestData
    4. This file should only be used for testing purpose. It's never part of production code
    5. all data loaded are marked as `active_in_mantis` by default
"""

from npsat_manager import models
from django.contrib.auth.models import User
from npsat_manager import load_data
from npsat_backend import settings
import os
import json
import random
import csv


data_folder = os.path.join(settings.BASE_DIR, "npsat_manager", "data")


def proportion_check(proportion):
    # check if proportion is between 1 and 0
    if proportion > 1 or proportion <= 0:
        raise ValueError("Proportion must be > 0 and <= 1.")


def load_resources(proportion=0.5):
    """
    load resources: scens, regions, crops,
    """
    proportion_check(proportion)
    load_regions(proportion, True)
    load_crops(proportion, True)
    load_scenarios()


def load_regions(proportion=0.5, ignore_check=False):
    """
    load regions proportionally from the dataset
    """
    if not ignore_check:
        proportion_check(proportion)

    load_counties(proportion, True)
    load_farms(proportion, True)
    load_central_valley()  # always load central valley
    load_basins()  # always load the 3 basins
    load_townships(proportion, True)
    load_b118_basin(proportion, True)


def load_counties(proportion=0.5, ignore_check=False):
    def counties_mantis_id_loader(data):
        county_name = data["name"]
        # strip any space in the name according to docs
        return county_name.replace(" ", "")

    if not ignore_check:
        proportion_check(proportion)
    county_file = os.path.join(
        settings.BASE_DIR,
        "npsat_manager",
        "data",
        "california-counties-1.0.0",
        "geojson",
        "california_counties_simplified_0005.geojson",
    )
    load_spec_regions(
        county_file,
        (("name", "name"), ("abcode", "external_id")),
        region_type=models.Region.COUNTY,
        mantis_id_loader=counties_mantis_id_loader,
        proportion=proportion,
    )  # , ("ansi", "ansi_code")))


def load_farms(proportion=0.5, ignore_check=False):
    def farms_mantis_id_loader(data):
        dwr = data["dwr_sbrgns"]
        return "Farm{}".format(dwr)

    if not ignore_check:
        proportion_check(proportion)
    field_map = (
        ("dwr_sbrgns", "external_id"),
        ("ShortName", "name"),
    )
    farm_file = os.path.join(
        settings.BASE_DIR,
        "npsat_manager",
        "data",
        "CVHM-farm",
        "geojson",
        "CVHM_farms_cleaned.geojson",
    )
    load_spec_regions(
        farm_file,
        field_map,
        region_type=models.Region.CVHM_FARM,
        mantis_id_loader=farms_mantis_id_loader,
        proportion=proportion,
    )


def load_central_valley():
    def central_valley_mantis_id_loader(data):
        return "CentralValley"

    central_valley_file = os.path.join(
        settings.BASE_DIR, "npsat_manager", "data", "central_valley.geojson"
    )
    load_spec_regions(
        central_valley_file,
        (("name", "name"), ("Id", "external_id")),
        region_type=models.Region.CENTRAL_VALLEY,
        mantis_id_loader=central_valley_mantis_id_loader,
        proportion=1,
    )


def load_basins():
    def basins_mantis_id_loader(data):
        return data["CVHM_Basin"].replace(" ", "")

    basin_file = os.path.join(
        settings.BASE_DIR, "npsat_manager", "data", "Basin", "geojson", "basin.geojson"
    )
    load_spec_regions(
        basin_file,
        (("CVHM_Basin", "name"), ("Basin_ID", "external_id")),
        region_type=models.Region.SUB_BASIN,
        mantis_id_loader=basins_mantis_id_loader,
        proportion=1,
    )


def load_townships(proportion=0.5, ignore_check=False):
    def townships_mantis_id_loader(data):
        return data["CO_MTR"]

    if not ignore_check:
        proportion_check(proportion)
    township_file = os.path.join(
        settings.BASE_DIR,
        "npsat_manager",
        "data",
        "townships",
        "geojson",
        "townships.geojson",
    )
    load_spec_regions(
        township_file,
        (("MTR", "name"), ("CO_MTR", "external_id")),
        region_type=models.Region.TOWNSHIPS,
        mantis_id_loader=townships_mantis_id_loader,
        proportion=proportion,
    )


def load_b118_basin(proportion=0.5, ignore_check=False):
    def b118_mantis_id_loader(data):
        return data["BAS_SBBSN"].replace("-", "_")

    if not ignore_check:
        proportion_check(proportion)
    b118_file = os.path.join(
        settings.BASE_DIR,
        "npsat_manager",
        "data",
        "B118",
        "B118_filtered_2018.geojsonl.json",
    )
    load_spec_regions(
        b118_file,
        (("SUBNAME", "name"), ("SUBBSN", "external_id")),
        region_type=models.Region.B118_BASIN,
        mantis_id_loader=b118_mantis_id_loader,
        proportion=proportion,
    )


def load_spec_regions(
    json_file, field_map, region_type, mantis_id_loader=None, proportion=0.5
):
    """
    Use proportion to randomly resample the record.
    """
    with open(json_file, "r") as input_data:
        geojson = input_data.readlines()

    if proportion != 1:
        random.shuffle(geojson)
        cutoff = int(len(geojson) * proportion)
        geojson = geojson[:cutoff]

    for record in geojson:
        # make a Python version of the JSON record
        python_data = json.loads(record)
        region = models.Region()  # make a new region object
        region.geometry = record  # save the whole JSON record as the geometry we'll send to the browser in the future

        for (
            fm
        ) in field_map:  # apply all the attributes to the region based on the field map
            value = python_data["properties"][fm[0]]
            if hasattr(
                region, fm[1]
            ):  # we need to check if that attribute exists first
                setattr(region, fm[1], value)  # if it does, set it on the region object
            setattr(region, "region_type", region_type)

        if mantis_id_loader:
            region.mantis_id = mantis_id_loader(python_data["properties"])
        region.save()  # save it with the new attributes


def load_scenarios():
    """
    load scenarios proportionally from the dataset
    since we have limited scenarios, all of them will be loaded
    ==================================================
    Note:
        1. This function depends on load_data. Update the function if there is any change.
    """
    load_data.load_scenarios()


def load_crops(proportion=0.5, ignore_check=False):
    """
    load crops proportionally from the dataset
    ====================================================
    Note:
        1. The loading here is without relationship
    """
    if not ignore_check:
        proportion_check(proportion)

    crop_csv = os.path.join(data_folder, "crops", "gnlm_swat_matched.csv")
    swat_name_field = "SWAT_Name"
    swat_id_field = "SWAT_Value"
    gnlm_name_field = "GNLM_Name"
    gnlm_id_field = "GNLM_Value"

    # add ALL Other Crops first
    models.Crop.objects.create(
        name="All Other Crops", crop_type=models.Crop.ALL_OTHER_CROPS
    )

    with open(crop_csv, "r") as csv_data:
        # turn dict reader to list for sampling
        crop_list = list(csv.DictReader(csv_data))

        if proportion != 1:
            random.shuffle(crop_list)
            cutoff = int(len(crop_list) * proportion)
            crop_list = crop_list[:cutoff]

        for record in crop_list:
            # make sure both the GNLM and SWAT variants exist
            try:
                swat_crop = models.Crop.objects.get(swat_code=record[swat_id_field])
            except models.Crop.DoesNotExist:
                swat_crop = models.Crop(
                    name=record[swat_name_field],
                    swat_code=record[swat_id_field],
                    crop_type=models.Crop.SWAT_CROP,
                )
                swat_crop.save()

            try:
                gnlm_crop = models.Crop.objects.get(caml_code=record[gnlm_id_field])
            except models.Crop.DoesNotExist:
                gnlm_crop = models.Crop(
                    name=record[gnlm_name_field],
                    caml_code=record[gnlm_id_field],
                    crop_type=models.Crop.GNLM_CROP,
                )
                gnlm_crop.save()

            # bidirectionally add relationships for them
            swat_crop.similar_crops.add(gnlm_crop)
            gnlm_crop.similar_crops.add(swat_crop)
            swat_crop.save()
            gnlm_crop.save()


def load_test_users():
    """
    This function loads 3 test normal users and 1 admin user
    """
    User.objects.create(username="test_user1", password="user1").save()
    User.objects.create(username="test_user2", password="user2").save()
    User.objects.create(username="test_user3", password="user3").save()

    User.objects.create(username="test_admin", password="admin").save()
    User.objects.create(username="service bot", password="admin").save()


def load_default_model_runs():
    """
    This function loads several BAU models
    =====================================================
    Note:
        1. load_test_users must be called before this function as models depend on their creator
        2. common resources must be loaded before this function
        3. After running the function:
            admin user has 3 BAU
            test_user1 has 1 public and 1 private model
            others don't have any models
    """

    load_data.load_system_admin_bot()
    # ensure admin presents in the database
    try:
        admin = User.objects.get(username="test_admin")
        test_user1 = User.objects.get(username="test_user1")
    except Exception as e:
        print(str(e))
        print("Error in retrieving admin user. Abort")
        raise e

    # create BAU
    BAU_CV_GNLM = models.ModelRun.objects.create(
        user=admin,
        name="BAU Central Valley GNLM",
        flow_scenario=models.Scenario.objects.get(name="CVHM_92_03_BUD0"),
        load_scenario=models.Scenario.objects.get(name="GNLM"),
        unsat_scenario=models.Scenario.objects.get(name="C2VSIM_SPRING_2015"),
        is_base=True,
        status=models.ModelRun.COMPLETED,
    )
    BAU_CV_GNLM.regions.add(models.Region.objects.get(name="Central Valley"))
    BAU_CV_GNLM.save()

    BAU_CV_SWAT1 = models.ModelRun.objects.create(
        user=admin,
        name="BAU Central Valley SWAT1",
        flow_scenario=models.Scenario.objects.get(name="CVHM_92_03_BUD0"),
        load_scenario=models.Scenario.objects.get(name="SWAT1"),
        unsat_scenario=models.Scenario.objects.get(name="C2VSIM_SPRING_2015"),
        is_base=True,
    )

    BAU_CV_SWAT1.regions.add(models.Region.objects.get(name="Central Valley"))
    BAU_CV_SWAT1.save()

    CV_test_user1_private = models.ModelRun.objects.create(
        user=test_user1,
        name="Central Valley SWAT1 private",
        flow_scenario=models.Scenario.objects.get(name="CVHM_92_03_BUD0"),
        load_scenario=models.Scenario.objects.get(name="SWAT1"),
        unsat_scenario=models.Scenario.objects.get(name="C2VSIM_SPRING_2015"),
        is_base=False,
        public=False,
    )

    CV_test_user1_private.save()

    CV_test_user1_public = models.ModelRun.objects.create(
        user=test_user1,
        name="Central Valley SWAT1 public",
        flow_scenario=models.Scenario.objects.get(name="CVHM_92_03_BUD0"),
        load_scenario=models.Scenario.objects.get(name="SWAT1"),
        unsat_scenario=models.Scenario.objects.get(name="C2VSIM_SPRING_2015"),
        is_base=False,
        public=True,
    )

    CV_test_user1_public.save()
