"""
test files for database of models: CRUD operations
====================================================
Note:
    1. isolate the loading file and any loading data with this test file
    2. since we are using the Django lib provided User models, no duplicated test here for users
"""

from django.test import TestCase
from npsat_manager import models
from django.db import transaction
from django.contrib.auth.models import User
from django.db import IntegrityError
from npsat_manager.tests import utils


class ResourcesTestCase(TestCase):
    """
    This class tests all sets of resources: regions, crops, scenarios
    """

    @classmethod
    def setUpTestData(cls):
        pass

    def test_regions_CRUD(self):
        """CR operations for regions; UD operations are not unnecessary for now"""
        with transaction.atomic():
            region_CV = models.Region.objects.create(
                name="Central Valley",
                region_type=models.Region.CENTRAL_VALLEY,
                external_id=1,
            )
            region_subbasin = models.Region.objects.create(
                name="Sac Basin",
                region_type=models.Region.SUB_BASIN,
                active_in_mantis=False,
            )
            region_CV.save()
            region_subbasin.save()

        with transaction.atomic():
            region_CV_db = models.Region.objects.get(name="Central Valley")
            region_subbasin_db = models.Region.objects.get(name="Sac Basin")

        # test read and write
        self.assertEqual(region_CV_db.name, "Central Valley")
        self.assertTrue(region_CV_db.active_in_mantis)
        self.assertEqual(region_CV_db.region_type, models.Region.CENTRAL_VALLEY)
        self.assertEqual(region_CV_db.external_id, "1")

        self.assertEqual(region_subbasin_db.name, "Sac Basin")
        self.assertFalse(region_subbasin_db.active_in_mantis)
        self.assertEqual(region_subbasin_db.region_type, models.Region.SUB_BASIN)
        self.assertEqual(region_subbasin_db.external_id, None)

    def test_scenarios_CRUD(self):
        """CR operations for scenarios; UD operations are not unnecessary for now"""
        with transaction.atomic():
            # force saving the instances using atomic trans
            scen_swat = models.Scenario.objects.create(
                name="SWAT",
                scenario_type=models.Scenario.TYPE_LOAD,
                crop_code_field=models.Scenario.SWAT_CROP,
            )
            scen_glnm = models.Scenario.objects.create(
                name="GLNM",
                scenario_type=models.Scenario.TYPE_LOAD,
                crop_code_field=models.Scenario.GNLM_CROP,
                active_in_mantis=False,
            )
            scen_cvhm = models.Scenario.objects.create(
                name="CVHM_2020", scenario_type=models.Scenario.TYPE_UNSAT
            )
            scen_swat.save()
            scen_glnm.save()
            scen_cvhm.save()

        with transaction.atomic():
            scen_swat_db = models.Scenario.objects.get(name="SWAT")
            scen_glnm_db = models.Scenario.objects.get(name="GLNM")
            scen_cvhm_db = models.Scenario.objects.get(name="CVHM_2020")

        # test read and write
        self.assertEqual(scen_swat_db.name, "SWAT")
        self.assertTrue(scen_swat_db.active_in_mantis)
        self.assertEqual(scen_swat_db.scenario_type, models.Scenario.TYPE_LOAD)
        self.assertEqual(scen_swat_db.crop_code_field, models.Scenario.SWAT_CROP)

        self.assertEqual(scen_cvhm_db.name, "CVHM_2020")
        self.assertTrue(scen_cvhm_db.active_in_mantis)
        self.assertEqual(scen_cvhm_db.scenario_type, models.Scenario.TYPE_UNSAT)
        self.assertEqual(scen_cvhm_db.crop_code_field, None)

        self.assertEquals(scen_glnm_db, scen_glnm)

    def test_crops_CRUD(self):
        """CR operations for crops; UD operations are not unnecessary for now"""
        with transaction.atomic():
            grape = models.Crop.objects.create(
                name="fake grape",
                crop_type=models.Crop.SWAT_CROP,
            )
            grape_type1 = models.Crop.objects.create(
                name="fake grape1",
                crop_type=models.Crop.GNLM_CROP,
                active_in_mantis=False,
            )
            grape_type2 = models.Crop.objects.create(
                name="fake grape2",
                crop_type=models.Crop.GNLM_CROP,
            )
            grape.similar_crops.add(grape_type1)
            grape.similar_crops.add(grape_type2)
            grape.save()
            grape_type1.save()
            grape_type2.save()

        with transaction.atomic():
            grape_db = models.Crop.objects.get(name="fake grape")
            grape_type1_db = models.Crop.objects.get(name="fake grape1")
            grape_type2_db = models.Crop.objects.get(name="fake grape2")

        # test read and write
        self.assertEqual(grape, grape_db)
        self.assertEqual(grape_type1, grape_type1_db)
        self.assertEqual(grape_type2, grape_type2_db)

        # test the reversed M2M relationship
        self.assertTrue(grape_type1_db.similar_backward.exists())
        self.assertTrue(grape_type2_db.similar_backward.exists())
        self.assertTrue(grape_db.similar_crops.exists())


class ModelRunTestCase(TestCase):
    """
    Test cases for model run related operations: CRUD

    Note:
        1. Now there isn't any privilege for super user with operations of model run.
            Tests for super user are skipped.
        2. There isn't any permission check at db level, so only one user instance is tested here.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Setting up users and some resources
        """
        utils.load_test_users()
        with transaction.atomic():
            # users
            User.objects.create(username="user1", password="user1").save()
            # regions
            models.Region.objects.create(
                name="Central Valley",
                region_type=models.Region.CENTRAL_VALLEY,
                mantis_id="CentralValley",
            ).save()
            models.Region.objects.create(
                name="Sac Basin",
                region_type=models.Region.SUB_BASIN,
            ).save()
            # scenarios
            models.Scenario.objects.create(
                name="SWAT",
                scenario_type=models.Scenario.TYPE_LOAD,
                crop_code_field=models.Scenario.SWAT_CROP,
            ).save()
            models.Scenario.objects.create(
                name="unsat",
                scenario_type=models.Scenario.TYPE_UNSAT,
            ).save()
            models.Scenario.objects.create(
                name="CVHM_2020", scenario_type=models.Scenario.TYPE_FLOW
            ).save()
            # crops
            models.Crop.objects.create(
                name="grape", crop_type=models.Crop.SWAT_CROP, swat_code=5
            ).save()
            models.Crop.objects.create(
                name="apple",
                crop_type=models.Crop.GNLM_CROP,
                active_in_mantis=False,
                swat_code=9,
            ).save()
            # default model run
            models.ModelRun.objects.create(
                user=User.objects.get(username="user1"),
                name="Default model",
                flow_scenario=models.Scenario.objects.get(
                    scenario_type=models.Scenario.TYPE_FLOW
                ),
                load_scenario=models.Scenario.objects.get(
                    scenario_type=models.Scenario.TYPE_LOAD
                ),
                unsat_scenario=models.Scenario.objects.get(
                    scenario_type=models.Scenario.TYPE_UNSAT
                ),
            ).save()

    def test_ModelRun_create(self):
        """test creation/save and the generated input message"""
        model_run1 = models.ModelRun.objects.create(
            user=User.objects.get(username="user1"),
            name="Model 1 by User 1 private",
            flow_scenario=models.Scenario.objects.get(
                scenario_type=models.Scenario.TYPE_FLOW
            ),
            load_scenario=models.Scenario.objects.get(
                scenario_type=models.Scenario.TYPE_LOAD
            ),
            unsat_scenario=models.Scenario.objects.get(
                scenario_type=models.Scenario.TYPE_UNSAT
            ),
        )
        model_run1.regions.add(models.Region.objects.get(name="Central Valley"))
        model_run1.modifications.add(
            models.Modification.objects.create(
                crop=models.Crop.objects.get(name="apple"), proportion=0.5
            )
        )
        model_run1.modifications.add(
            models.Modification.objects.create(
                crop=models.Crop.objects.get(name="grape"), proportion=0.7
            )
        )
        model_run1.save()
        self.assertEqual(
            model_run1.input_message,
            "endSimYear 2300 startRed 2020 endRed 2025 flowScen CVHM_2020 loadScen SWAT "
            "unsatScen unsat unsatWC 0 bMap CentralValley Nregions 1 CentralValley "
            "Ncrops 1 5 0.7000 ENDofMSG\n",
        )

    def test_ModelRun_read(self):
        """test read to check default values if not specified"""
        model_run1 = models.ModelRun.objects.get(
            name="Default model",
        )
        self.assertEqual(model_run1.sim_end_year, 2300)
        self.assertEqual(model_run1.reduction_start_year, 2020)
        self.assertEqual(model_run1.reduction_end_year, 2025)
        self.assertEqual(model_run1.is_base, False)
        self.assertEqual(model_run1.public, False)

    def test_ModelRun_update(self):
        """test publishing model"""
        # update
        with transaction.atomic():
            model_default = models.ModelRun.objects.get(name="Default model")
            model_default.public = True
            model_default.save()

        # read back and test
        model_default = models.ModelRun.objects.get(
            name="Default model",
        )
        self.assertEqual(model_default.public, True)

    def test_ModelRun_delete(self):
        """test delete and probably bulk delete(if we re-enable the feature)"""
        # create unrelated random model runs
        with transaction.atomic():
            for i in range(5):
                model_to_be_deleted = models.ModelRun.objects.create(
                    name="Model to be deleted {}".format(i),
                    user=User.objects.get(username="user1"),
                    flow_scenario=models.Scenario.objects.get(
                        scenario_type=models.Scenario.TYPE_FLOW
                    ),
                    load_scenario=models.Scenario.objects.get(
                        scenario_type=models.Scenario.TYPE_LOAD
                    ),
                    unsat_scenario=models.Scenario.objects.get(
                        scenario_type=models.Scenario.TYPE_UNSAT
                    ),
                )
                model_to_be_deleted.regions.add(
                    models.Region.objects.get(name="Sac Basin")
                )
                model_to_be_deleted.modifications.add(
                    models.Modification.objects.create(
                        crop=models.Crop.objects.get(name="apple"), proportion=0.5
                    )
                )
                model_to_be_deleted.modifications.add(
                    models.Modification.objects.create(
                        crop=models.Crop.objects.get(name="grape"), proportion=0.7
                    )
                )

        # delete single model
        model_to_be_deleted = models.ModelRun.objects.get(name="Model to be deleted 1")
        deleted_model_id_copy = model_to_be_deleted.id
        model_to_be_deleted.delete()

        # check if model still in the db
        self.assertEqual(
            len(models.ModelRun.objects.filter(name="Model to be deleted 1")), 0
        )
        # check if modifications are deleted
        self.assertEqual(
            len(models.Modification.objects.filter(model_run_id=deleted_model_id_copy)),
            0,
        )
        # check if assets(regions/scens...) are deleted
        self.assertEqual(len(models.Region.objects.all()), 2)
        self.assertEqual(len(models.Crop.objects.all()), 2)
        self.assertEqual(len(models.Scenario.objects.all()), 3)
