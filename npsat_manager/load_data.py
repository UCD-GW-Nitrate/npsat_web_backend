import csv
import os
import json
from itertools import product

from npsat_backend import settings

from npsat_manager import models
from npsat_backend import local_settings
from npsat_manager.models import CustomUser

data_folder = os.path.join(settings.BASE_DIR, "npsat_manager", "data")


def load_all(mantis_port_number=5941):
    load_all_data()
    load_mantis_server(mantis_port_number=mantis_port_number)
    load_system_admin_bot()

def load_all_data():
    # load_crops() -- No longer using this one
    # load_only_gnlm_crops()
    # load_regions()
    # load_scenarios()
    # load_wells()
    load_wells_age()


def load_system_admin_bot():
    CustomUser.objects.create(
        username=local_settings.ADMIN_BOT_USERNAME,
        password=local_settings.ADMIN_BOT_PASSWORD,
    )


def load_scenarios():
    enable_scenario_dev_data()


def load_mantis_server(mantis_port_number):
    models.MantisServer.objects.create(host="127.0.0.1", port=mantis_port_number)


def load_regions():
    load_counties()
    load_farms()
    load_central_valley()
    load_basins()
    load_townships()
    load_b118_basin()

def load_wells(
    well_csv=os.path.join(data_folder, "wells", "wells.csv"),
    flow_model_field = "FlowModel",
    rch_type_field = "RchType",
    well_type_field = "WellType",
    eid_field = "Eid",
    x_field = "X",
    y_field = "Y",
    lat_field = "Lat",
    lon_field = "Lon",
    unsat_field = "UNSAT",
    wt2t_field = "WT2T",
    slmod_field = "SLmod",
    basin_field = "Basin",
    county_field = "County",
    b118_field = "B118",
    tship_field = "Tship",
    subReg_field = "SubReg",
):
    with open(well_csv, "r") as csv_data:
        well_list = csv.DictReader(csv_data)

        for record in well_list:
            try:
                well = models.Well.objects.get(
                    flow_model=record[flow_model_field],
                    rch_type=record[rch_type_field],
                    well_type=record[well_type_field],
                    eid=record[eid_field],
                    x=record[x_field],
                    y=record[y_field],
                    lat=record[lat_field],
                    lon=record[lon_field],
                    unsat=record[unsat_field],
                    wt2t=record[wt2t_field],
                    slmod=record[slmod_field],
                    depth=float(record[unsat_field]) + float(record[wt2t_field]) + float(record[slmod_field]),
                    basin=record[basin_field],
                    county=record[county_field],
                    b118=record[b118_field],
                    tship=record[tship_field],
                    subreg=record[subReg_field],
                )
                print("existing " + str(well.eid))
                continue
            except models.Well.DoesNotExist:
                well = models.Well(
                    flow_model=record[flow_model_field],
                    rch_type=record[rch_type_field],
                    well_type=record[well_type_field],
                    eid=record[eid_field],
                    x=record[x_field],
                    y=record[y_field],
                    lat=record[lat_field],
                    lon=record[lon_field],
                    unsat=record[unsat_field],
                    wt2t=record[wt2t_field],
                    slmod=record[slmod_field],
                    depth=float(record[unsat_field]) + float(record[wt2t_field]) + float(record[slmod_field]),
                    basin=record[basin_field],
                    county=record[county_field],
                    b118=record[b118_field],
                    tship=record[tship_field],
                    subreg=record[subReg_field],
                )
                well.save()
                print("new " + str(well.eid))


def load_wells_age(
    csv_dir=os.path.join(data_folder, "wells_age_data"),
    flow_models = ["C2VSim", "CVHM2"],
    rch_types = ["Padj", "Radj"],
    well_types = ["VD", "VI"],
    eid_field = "Eid",
    pumping_field = "Q_m3d",
    sid_field = "Sid",
    lat_field = "Lat",
    lon_field = "Lon",
    len_field = "Len",
    in_river_field = "InRiver",
    wt2d_field = "WT2D",
    age_a_field = "Age_a",
    age_b_field = "Age_b",
):
    for flow_model, rch_type, well_type in product(flow_models, rch_types, well_types):
        well_csv = csv_dir + f"/wells_{flow_model.lower()}_{rch_type.lower()}_{well_type.lower()}.csv"
        urf_csv = csv_dir + f"/urf_{flow_model.lower()}_{rch_type.lower()}_{well_type.lower()}.csv"

        with open(well_csv, "r") as csv_data:
            well_list = csv.DictReader(csv_data)
            for record in well_list:
                try:
                    well = models.Well.objects.get(
                        flow_model=flow_model,
                        rch_type=rch_type,
                        well_type=well_type,
                        eid=record[eid_field],
                    )
                    well.pumping = record[pumping_field]
                    print("update eid " + str(well.eid))
                except models.Well.DoesNotExist:
                    print("missing eid" + str(record[eid_field]))

        with open(urf_csv, "r") as csv_data:
            urf_list = csv.DictReader(csv_data)
            for record in urf_list:
                try:
                    well = models.Well.objects.get(
                        flow_model=flow_model,
                        rch_type=rch_type,
                        well_type=well_type,
                        eid=record[eid_field],
                    )    
                
                    urf_point, created = models.URFPoint.objects.get_or_create(
                        flow_model=flow_model,
                        rch_type=rch_type,
                        well_type=well_type,
                        sid=record[sid_field],
                        lat=record[lat_field],
                        lon=record[lon_field],
                        length=record[len_field],
                        in_river=record[in_river_field],
                        wt2d=record[wt2d_field],
                        age_a=record[age_a_field],
                        age_b=record[age_b_field],
                        well=well,
                    )
                    if created:
                        print(f"new sid {urf_point.sid}")
                    else:
                        print(f"exists sid {str(record[sid_field])}")
                except models.Well.DoesNotExist:
                    continue


def load_crops(
    crop_csv=os.path.join(data_folder, "crops", "gnlm_swat_matched.csv"),
    swat_name_field="SWAT_Name",
    swat_id_field="SWAT_Value",
    gnlm_name_field="GNLM_Name",
    gnlm_id_field="GNLM_Value",
    group_field="CropGroup_LanduseGroup",
):
    """
            The crop loading here is very basic - it does add some relationships, but they're not all correct yet.
            It's good enough for now though. I'm only loading the SWAT->GNLM data and not the other way around, technically,
            except I load it as both (that is, the GNLM crops have the SWAT relationships still, but they might not be
            right for the long run). It also doesn't load groups yet. No crop has both a GNLM and a SWAT code right now
             - they all have only one or the other. I might keep things that way
    :return:
    """

    # add ALL Other Crops first
    if models.Crop.objects.filter(name="All Other Crops").count() == 0:
        models.Crop.objects.create(
            name="All Other Crops", crop_type=models.Crop.ALL_OTHER_CROPS
        )
    
    for crop in models.Crop.objects.all():
        crop.active_in_mantis = False
        crop.save()

    try:
        all_other_crops = models.Crop.objects.get(name="All Other Crops")
        all_other_crops.active_in_mantis = True
        all_other_crops.save()
    except models.Crop.DoesNotExist:
        pass

    with open(crop_csv, "r") as csv_data:
        crop_list = csv.DictReader(csv_data)

        for record in crop_list:
            # make sure both the GNLM and SWAT variants exist
            try:
                swat_crop = models.Crop.objects.get(
                    swat_code=record[swat_id_field], 
                    crop_type=models.Crop.SWAT_CROP,
                )
                swat_crop.name=record[swat_name_field]
                swat_crop.active_in_mantis = True
                swat_crop.save()
            except models.Crop.DoesNotExist:
                swat_crop = models.Crop(
                    name=record[swat_name_field],
                    swat_code=record[swat_id_field],
                    crop_type=models.Crop.SWAT_CROP,
                )
                swat_crop.save()

            try:
                gnlm_crop = models.Crop.objects.get(
                    caml_code=record[gnlm_id_field],
                    crop_type=models.Crop.GNLM_CROP,
                )
                gnlm_crop.name=record[gnlm_name_field]
                gnlm_crop.active_in_mantis = True
                gnlm_crop.save()
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


def load_only_gnlm_crops(
    crop_csv=os.path.join(data_folder, "crops", "GNLM_LU_3_26.csv"),
    gnlm_name_field="LU_Name",
    gnlm_id_field="DWR_CAML_Code",
):
    """
            The crop loading here is reflective of changes in Mantis, where only GNLM Load Scenarios are available to the user.
            Newly added GNLM crop which were't existing from previous load_crops runs will not have bidirectional swat 
            relationship, since they aren't defined by the target csv
    :return:
    """

    # add ALL Other Crops first
    if models.Crop.objects.filter(name="All Other Crops").count() == 0:
        models.Crop.objects.create(
            name="All Other Crops", crop_type=models.Crop.ALL_OTHER_CROPS
        )
    
    for crop in models.Crop.objects.all():
        crop.active_in_mantis = False
        crop.save()

    try:
        all_other_crops = models.Crop.objects.get(name="All Other Crops")
        all_other_crops.active_in_mantis = True
        all_other_crops.save()
    except models.Crop.DoesNotExist:
        pass

    with open(crop_csv, "r") as csv_data:
        crop_list = csv.DictReader(csv_data)

        for record in crop_list:
            try:
                gnlm_crop = models.Crop.objects.get(
                    caml_code=record[gnlm_id_field],
                    crop_type=models.Crop.GNLM_CROP,
                )
                gnlm_crop.name=record[gnlm_name_field]
                gnlm_crop.active_in_mantis = True
                gnlm_crop.save()
            except models.Crop.DoesNotExist:
                gnlm_crop = models.Crop(
                    name=record[gnlm_name_field],
                    caml_code=record[gnlm_id_field],
                    crop_type=models.Crop.GNLM_CROP,
                )
                gnlm_crop.save()


def load_counties():
    """
    :return:
    """

    def counties_mantis_id_loader(data):
        county_name = data["name"]
        # strip any space in the name according to docs
        return county_name.replace(" ", "")

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
    )  # , ("ansi", "ansi_code")))

    enable_default_counties(
        all=True
    )  # all is True just for testing - we'll set this to False later


def load_farms():
    """
    :return:
    """

    def farms_mantis_id_loader(data):
        dwr = data["dwr_sbrgns"]
        return "Subregion{}".format(dwr)

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
    )


def load_townships():
    def townships_mantis_id_loader(data):
        return data["CO_MTR"]

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
    )


def load_b118_basin():
    def b118_mantis_id_loader(data):
        return data["BAS_SBBSN"].replace("-", "_").replace(".", "_")

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
    )


def load_spec_regions(json_file, field_map, region_type, mantis_id_loader=None):
    """
            Given a geojson file, loads each record as a county instance, assigning data
            to fields by the field map. The geojson file isn't a standard file, but instead just
            the individual records for each feature, with no enclosing array, one per line (as saved by
            QGIS in a specific format, with newline delimited)

            Warning: It loads the *whole* geojson record in as geometry, even attributes that
            aren't in the field map, so all attributes will be sent to the client. If you don't
            want this or want a leaner GeoJSON, strip unnecessary information out before loading
    :param json_file: newline delimited GeoJSON file (QGIS can export this) of the regions
    :param field_map: iterable of two-tuples. First value is the field in the datasets,
                                    and the second is the field here in npsat_manager (think "from", "to")
    :param model_area: The model area instance to attach these regions to
    :return:
    """

    with open(json_file, "r") as input_data:
        geojson = input_data.readlines()

    if mantis_id_loader:
        regions = models.Region.objects.filter(region_type=region_type)
        for region in regions:
            region.active_in_mantis = False
            region.save()

    for record in geojson:
        # make a Python version of the JSON record
        python_data = json.loads(record)

        try:
            if mantis_id_loader:
                filter_criteria = {}
                for ( fm ) in field_map:
                    filter_criteria[fm[1]] = python_data["properties"][fm[0]]

                existing_region = models.Region.objects.get(mantis_id=mantis_id_loader(python_data["properties"]), **filter_criteria)
                existing_region.active_in_mantis = True
                existing_region.save()
                continue
        except models.Region.DoesNotExist:
            pass

        region = models.Region()  # make a new region object
        region.geometry = record  # save the whole JSON record as the geometry we'll send to the browser in the future

        for ( fm ) in field_map:  # apply all the attributes to the region based on the field map
            value = python_data["properties"][fm[0]]
            if hasattr(
                region, fm[1]
            ):  # we need to check if that attribute exists first
                setattr(region, fm[1], value)  # if it does, set it on the region object
            setattr(region, "region_type", region_type)

        if mantis_id_loader:
            region.mantis_id = mantis_id_loader(python_data["properties"])

        region.save()  # save it with the new attributes


def enable_default_counties(enable_counties=("Tulare",), all=False):
    """
            By default, we consider counties inactive so they don't show in the list if we can't use them.

            If all=True, ignores enable_counties and just enables all counties. When False, only enables counties whose
            names are in the list
    :return:
    """
    if all:
        counties = []
        for county in models.Region.objects.all():
            county.active_in_mantis = True
            counties.append(county)
        models.Region.objects.bulk_update(counties, ["active_in_mantis"])
    else:
        for county in enable_counties:
            update_county = models.Region.objects.get(name=county)
            update_county.active_in_mantis = True
            update_county.save()


def enable_region_dev_data(enable_regions=("Central Valley",), all=False):
    """
            For dev purpose, enable all regions

            If all=True, ignores enable_counties and just enables all counties. When False, only enables counties whose
            names are in the list
    :return:
    """
    if all:
        regions = []
        for region in models.Region.objects.all():
            region.active_in_mantis = True
            regions.append(region)
        models.Region.objects.bulk_update(regions, ["active_in_mantis"])
    else:
        for county in enable_regions:
            update_region = models.Region.objects.get(name=county)
            update_region.active_in_mantis = True
            update_region.save()


def enable_scenario_dev_data():
    scenarios_csv = os.path.join(data_folder, "scenarios", "MantisScenariosNames.csv")
    with open(scenarios_csv, "r") as scenario_data:
        scenario_list = csv.DictReader(scenario_data)
        for scenario in models.Scenario.objects.all():
            scenario.active_in_mantis = False
            scenario.save()

        for scenario in scenario_list:
            try:
                existing_scenario = models.Scenario.objects.get(
                    mantis_id=scenario["Code name"],
                )
                existing_scenario.name = scenario["User friendly name"]
                existing_scenario.description = scenario["Short description"]
                existing_scenario.long_description = scenario["Long description"]
                existing_scenario.external_url = scenario["url"]
                existing_scenario.active_in_mantis = True
                existing_scenario.save()
                continue
            except models.Scenario.DoesNotExist:
                pass

            category = scenario["Category"]
            crop_code_field = None
            if category == "Load Scenario":
                scenario_type = models.Scenario.TYPE_LOAD
                crop_code_field = models.Scenario.GNLM_CROP
            elif category == "Flow Scenario":
                scenario_type = models.Scenario.TYPE_FLOW
            elif category == "Well Type Scenario":
                scenario_type = models.Scenario.TYPE_WELLTYPE
            else:
                scenario_type = models.Scenario.TYPE_UNSAT
            models.Scenario.objects.create(
                name=scenario["User friendly name"],
                mantis_id=scenario["Code name"],
                description=scenario["Short description"],
                long_description=scenario["Long description"],
                external_url=scenario["url"],
                scenario_type=scenario_type,
                crop_code_field=crop_code_field
            ).save()
