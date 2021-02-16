"""
test files for external APIs exposed for front end and public
====================================================
Note:
    1. some parts of the serializer are not tested here
    2. several data should be loaded prior to the testing; see setUpClass for details
"""

from django.test import TestCase
from rest_framework.test import APIClient
from npsat_manager import models
from npsat_manager.tests import utils
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User


class APITestCase(TestCase):
    """
    Test for all APIs:
        single operation tests
    """

    @classmethod
    def setUpTestData(cls):
        """set up common resources and some fake users/models"""
        utils.load_resources(0.2)
        utils.load_test_users()
        utils.load_default_model_runs()

    def test_region_read(self):
        """
        Test region read
        ===================================
        Note:
            1. No create/delete operation by admin user is tested here
        """
        # test cases when user doesn't log in
        client_no_login = APIClient()
        res = client_no_login.get("/api/region/?limit=1000")
        self.assertEqual(len(res.data["results"]), models.Region.objects.count())

        # It is what the api is going to be used mostly
        for region_tuple in models.Region.REGION_TYPE:
            region_code, region_name = region_tuple
            print("Testing {} filter on region API without login...".format(region_name))
            res = client_no_login.get("/api/region/?region_type={}&limit=1000".format(region_code))
            self.assertEqual(len(res.data["results"]),
                             models.Region.objects.filter(region_type=region_code).count())

        # test cases when user logs in
        # we have already loaded user
        token = Token.objects.get(user__username='test_user2')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        res = client_logged_in.get("/api/region/?limit=1000")
        self.assertEqual(len(res.data["results"]), models.Region.objects.count())

        for region_tuple in models.Region.REGION_TYPE:
            region_code, region_name = region_tuple
            print("Testing {} filter on region API when login...".format(region_name))
            res = client_logged_in.get("/api/region/?region_type={}&limit=1000".format(region_code))
            self.assertEqual(len(res.data["results"]),
                             models.Region.objects.filter(region_type=region_code).count())

    def test_scenario_read(self):
        """
        Test all scenarios read
        ======================================
        Note:
            1. No create/delete operation by admin user is tested here
        """
        # test cases when user doesn't log in
        client_no_login = APIClient()
        res = client_no_login.get("/api/scenario/")
        self.assertEqual(len(res.data["results"]), models.Scenario.objects.count())

        for scenario_tuple in models.Scenario.SCENARIO_TYPE:
            scenario_code, scenario_name = scenario_tuple
            print("Testing {} filter on scenario API without login...".format(scenario_name))
            res = client_no_login.get("/api/scenario/?scenario_type={}".format(scenario_code))
            self.assertEqual(len(res.data["results"]),
                             models.Scenario.objects.filter(scenario_type=scenario_code).count())

        # test cases when user logs in
        # we have already loaded user
        token = Token.objects.get(user__username='test_user2')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        res = client_logged_in.get("/api/scenario/")
        self.assertEqual(len(res.data["results"]), models.Scenario.objects.count())

        for scenario_tuple in models.Scenario.SCENARIO_TYPE:
            scenario_code, scenario_name = scenario_tuple
            print("Testing {} filter on scenario API when logged in...".format(scenario_name))
            res = client_logged_in.get("/api/scenario/?scenario_type={}".format(scenario_code))
            self.assertEqual(len(res.data["results"]),
                             models.Scenario.objects.filter(scenario_type=scenario_code).count())

    def test_crop_read(self):
        """
        Test all crop read
        ======================================
        Note:
            1. No create/delete operation by admin user is tested here
        """
        SWAT_scen = models.Scenario.objects.get(name="SWAT1")
        GNLM_scen = models.Scenario.objects.get(name="GNLM")
        crop_type_list = [models.Crop.ALL_OTHER_CROPS, models.Crop.GENERAL_CROP]
        # test cases when user doesn't log in
        # It is only possible in the production to query crops based on type
        client_no_login = APIClient()
        res = client_no_login.get("/api/crop/")
        self.assertEqual(len(res.data["results"]), models.Crop.objects.count())

        print("Testing {} filter on crop API without login...".format(SWAT_scen.name))
        res = client_no_login.get("/api/crop/?flow_scenario={}".format(SWAT_scen.id))
        self.assertEqual(len(res.data["results"]), models.Crop.objects.filter(
            crop_type__in=[*crop_type_list, models.Crop.SWAT_CROP]
        ).count())

        print("Testing {} filter on crop API without login...".format(GNLM_scen.name))
        res = client_no_login.get("/api/crop/?flow_scenario={}".format(GNLM_scen.id))
        self.assertEqual(len(res.data["results"]), models.Crop.objects.filter(
            crop_type__in=[*crop_type_list, models.Crop.GNLM_CROP]
        ).count())

        # test cases when user logs in
        # we have already loaded user
        token = Token.objects.get(user__username='test_user2')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        print("Testing {} filter on crop API when logged in...".format(SWAT_scen.name))
        res = client_no_login.get("/api/crop/?flow_scenario={}".format(SWAT_scen.id))
        self.assertEqual(len(res.data["results"]), models.Crop.objects.filter(
            crop_type__in=[*crop_type_list, models.Crop.SWAT_CROP]
        ).count())

        print("Testing {} filter on crop API when logged in...".format(GNLM_scen.name))
        res = client_no_login.get("/api/crop/?flow_scenario={}".format(GNLM_scen.id))
        self.assertEqual(len(res.data["results"]), models.Crop.objects.filter(
            crop_type__in=[*crop_type_list, models.Crop.GNLM_CROP]
        ).count())

    """
    Below are the tests of endpoints of model run. Each focuses on a specific feature.
    ====================================
    Note:
        1. Serializers are tested by Django. We will only check if some fields are correctly
            outputted in the response
    """

    def test_model_run_read(self):
        """
        Test read in model run endpoints.
        This endpoint is mainly used for overview and details
        """
        # without login
        # User who doesn't login can not pass the check
        client_no_login = APIClient()
        res = client_no_login.get("/api/model_run")
        self.assertEqual(res.status_code, 301)

        # user login: overview and details access are authentication required
        token = Token.objects.get(user__username='test_user3')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        # overview and any other general retrieval from the endpoints
        res = client_logged_in.get("/api/model_run/")
        self.assertEqual(len(res.data["results"]), 3)  # we only have 2 base model and 1 public

        test_modelRun_instance_db = models.ModelRun.objects.get(name="BAU Central Valley GNLM")
        res = client_logged_in.get("/api/model_run/{}/".format(test_modelRun_instance_db.id))
        test_modelRun_instance_API = res.data
        # check some important fields
        self.assertEqual(test_modelRun_instance_API["id"], test_modelRun_instance_db.id)
        self.assertEqual(test_modelRun_instance_API["name"], test_modelRun_instance_db.name)
        self.assertEqual(test_modelRun_instance_API["user"], test_modelRun_instance_db.user.id)

        # try to access private model from other people
        test_modelRun_instance_db = models.ModelRun.objects.get(name="Central Valley SWAT1 private")
        res = client_logged_in.get("/api/model_run/{}/".format(test_modelRun_instance_db.id))
        self.assertEqual(res.status_code, 404)

        # switch user to test_user1
        token = Token.objects.get(user__username='test_user1')
        # by docs, the credentials are overwritten
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        res = client_logged_in.get("/api/model_run/")
        self.assertEqual(len(res.data["results"]), 4)  # 2 base model, 1 public, and 1 private

        # access one's own private model run
        res = client_logged_in.get("/api/model_run/{}/".format(test_modelRun_instance_db.id))
        self.assertEqual(res.status_code, 200)

    def test_model_run_search(self):
        """
        Test searching of model runs endpoint
        This endpoint is mainly used for filtering and searching
        ==============================================
        Note:
            1. general get request are tested in the below function, so non-login cases will not
                be tested here
            2. Non login user are tested in the above example as a more general url endpoint
        """

        # user login: overview and details access are authentication required
        token = Token.objects.get(user__username='test_user3')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        # overview filter
        res = client_logged_in.get("/api/model_run/?public=False&isBase=False")
        self.assertEqual(len(res.data["results"]), 0)  # no models after above filter

        # search
        res = client_logged_in.get("/api/model_run/?search=SWAT1")
        self.assertEqual(len(res.data["results"]), 2)

        res = client_logged_in.get("/api/model_run/?search=Central&status={}".format(
            models.ModelRun.COMPLETED
        ))
        self.assertEqual(len(res.data["results"]), 1)

        GNLM_scen = models.Scenario.objects.get(name="GNLM")
        res = client_logged_in.get("/api/model_run/?scenarios={}".format(
            GNLM_scen.id
        ))
        self.assertEqual(len(res.data["results"]), 1)

        # switch to test_user1 and test again
        # difference is that test_user1 has some created model runs
        token = Token.objects.get(user__username='test_user1')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        # overview filter
        res = client_logged_in.get("/api/model_run/?public=False&isBase=False")
        self.assertEqual(len(res.data["results"]), 2)

        # search
        res = client_logged_in.get("/api/model_run/?search=SWAT1")
        self.assertEqual(len(res.data["results"]), 3)

        res = client_logged_in.get("/api/model_run/?search=Central&status={}".format(
            models.ModelRun.COMPLETED
        ))
        self.assertEqual(len(res.data["results"]), 1)

        GNLM_scen = models.Scenario.objects.get(name="GNLM")
        res = client_logged_in.get("/api/model_run/?scenarios={}".format(
            GNLM_scen.id
        ))
        self.assertEqual(len(res.data["results"]), 1)

    def test_model_run_create(self):
        """
        Test model run creation
        """
        # some pre-loaded resources
        crops = models.Crop.objects.filter(active_in_mantis=True)
        regions = models.Region.objects.filter(region_type=models.Region.CVHM_FARM)
        user1 = User.objects.get(username="test_user1")
        flow_scen = models.Scenario.objects.get(name="CVHM_92_03_BUD0")
        unsat_scen = models.Scenario.objects.get(name="GNLM")
        load_scen = models.Scenario.objects.get(name="C2VSIM_SPRING_2015")
        # test with non login user
        client_no_login = APIClient()

        # test access
        data = {
            "name": "Test Model Run POST endpoint 1",
            "modifications": [
                {
                    "crop": {
                        "id": crop.id
                    },
                    "proportion": 0.5
                } for crop in crops
            ],
            "regions": [
                {
                    "id": region.id
                } for region in regions
            ],
            "unsat_scenario": {"id": unsat_scen.id},
            "flow_scenario": {"id": flow_scen.id},
            "load_scenario": {"id": load_scen.id}
        }
        res = client_no_login.post("/api/model_run/", data, format="json")
        self.assertEqual(res.status_code, 401)

        # test logged in user
        token = Token.objects.get(user__username='test_user1')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        res = client_logged_in.post("/api/model_run/", data, format="json")
        self.assertEqual(res.status_code, 201)

        # check if the model and the BAU model is created
        self.assertEqual(models.ModelRun.objects.filter(name="BAU model").count(), 1)

        # switch to test user 2
        token = Token.objects.get(user__username='test_user2')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        res = client_logged_in.post("/api/model_run/", data, format="json")
        self.assertEqual(res.status_code, 201)

        # check if the model and the BAU model is created; it should not because we already have one
        self.assertEqual(models.ModelRun.objects.filter(name="BAU model").count(), 1)

    def test_model_run_delete(self):
        """
        Test model run deletion(single)
        """
        # retrieve ids of test model run
        BAU_model_run = models.ModelRun.objects.get(name="BAU Central Valley GNLM")
        # below two model runs belong to test user 1
        private_model_run = models.ModelRun.objects.get(name="Central Valley SWAT1 private")
        public_model_run = models.ModelRun.objects.get(name="Central Valley SWAT1 public")

        # non user login test cases
        client_no_login = APIClient()
        res = client_no_login.delete("/api/model_run/{}/".format(BAU_model_run.id))
        self.assertEqual(res.status_code, 401)

        # login test user 2 and try to remove models created by others
        token = Token.objects.get(user__username='test_user2')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        res = client_logged_in.delete("/api/model_run/{}/".format(BAU_model_run.id))
        self.assertEqual(res.status_code, 403)
        res = client_logged_in.delete("/api/model_run/{}/".format(private_model_run.id))
        self.assertEqual(res.status_code, 404)
        res = client_logged_in.delete("/api/model_run/{}/".format(public_model_run.id))
        self.assertEqual(res.status_code, 403)

        # switch to test user 1 and try to remove the models created by test user 1
        token = Token.objects.get(user__username='test_user1')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        res = client_logged_in.delete("/api/model_run/{}/".format(BAU_model_run.id))
        self.assertEqual(res.status_code, 403)
        res = client_logged_in.delete("/api/model_run/{}/".format(private_model_run.id))
        self.assertEqual(res.status_code, 204)
        res = client_logged_in.delete("/api/model_run/{}/".format(public_model_run.id))
        self.assertEqual(res.status_code, 204)

    def test_model_run_update(self):
        """
        Test updating model
        This endpoint is mainly used for publishing the model
        ===========================================================
        Note:
            1. It is not a comprehensive test on the PUT method, but only tests the functionality of it
            2. Power users are able to break model attributes and modify to whatever they want through this endpoint
            3. Add future tests if we want to limit the capability of this endpoint
            4. PATCH method is disabled in the model viewset
        """
        # retrieve ids of test model run
        BAU_model_run = models.ModelRun.objects.get(name="BAU Central Valley GNLM")
        # below two model runs belong to test user 1
        private_model_run = models.ModelRun.objects.get(name="Central Valley SWAT1 private")
        public_model_run = models.ModelRun.objects.get(name="Central Valley SWAT1 public")

        # test with non login user
        client_no_login = APIClient()

        # test access
        data = {"public": False}
        res = client_no_login.put("/api/model_run/{}/".format(BAU_model_run.id), data, format="json")
        self.assertEqual(res.status_code, 401)

        # test with logged in user to change other users' models
        token = Token.objects.get(user__username='test_user3')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        res = client_logged_in.put("/api/model_run/{}/".format(private_model_run.id), data, format="json")
        self.assertEqual(res.status_code, 404)

    def test_model_run_status(self):
        """
        Test the endpoint to get model status by giving ids
        """

        # test with non login user
        client_no_login = APIClient()
        model_id_1 = models.ModelRun.objects.get(id=1)
        model_id_2 = models.ModelRun.objects.get(id=2)
        model_id_3 = models.ModelRun.objects.get(id=3)

        # test access
        model_ids = ",".join(["1", "2", "3"])
        res = client_no_login.get("/api/model_run__status/?ids={}".format(model_ids), format="json")
        self.assertEqual(res.status_code, 401)

        # test with logged in user to change other users' models
        token = Token.objects.get(user__username='test_user1')
        client_logged_in = APIClient()
        client_logged_in.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        res = client_logged_in.get("/api/model_run__status/?ids={}".format(model_ids), format="json")
        self.assertEqual(res.status_code, 200)

        # test without required params
        res = client_logged_in.get("/api/model_run__status/", format="json")
        self.assertEqual(res.status_code, 400)

        # test output
        res = client_logged_in.get("/api/model_run__status/?ids={}".format(model_ids), format="json")
        self.assertEqual(res.status_code, 200)
        test_data = [model_id_1, model_id_2, model_id_3]
        for i in range(len(test_data)):
            self.assertEqual(test_data[i].name, res.data["results"][i]["name"])
            self.assertEqual(test_data[i].id, res.data["results"][i]["id"])
            self.assertEqual(test_data[i].status, res.data["results"][i]["status"])

        # test model DNE
        # we don't have model with id 6
        res = client_logged_in.get("/api/model_run__status/?ids={}".format("6"), format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(-1, res.data["results"][0]["status"])


class StimulationAPITest(TestCase):
    """
    Stimulate front end queries
    """

    @classmethod
    def setUpTestData(cls):
        utils.load_resources(0.5)
        utils.load_test_users()
        utils.load_default_model_runs()
