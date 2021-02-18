import time

import requests

apidemo_token = "e0a132761aa8d1168542b53648ee044f33c7bf65"  # replace this with a valid API token - this one only works in my local sqlite.
auth_header = {"Authorization": "Token {}".format(apidemo_token)}

# Step 1: Create the Model Run
create_run = requests.post(
    "http://localhost:8000/api/model_run/",
    headers=auth_header,
    data={"user": 4, "name": "API Test"},
)
print(create_run.json())

model_run_id = create_run.json()["id"]  # get the ID of the newly created model run

# set the IDs in the DB for corn and grapes, as used in the demo
corn = 1
grapes = 2

corn_modification = requests.post(
    "http://localhost:8000/api/modification/",
    headers=auth_header,
    data={"model_run": model_run_id, "crop": corn, "proportion": 0.5},
)
print(corn_modification.text)
grapes_modification = requests.post(
    "http://localhost:8000/api/modification/",
    headers=auth_header,
    data={"model_run": model_run_id, "crop": grapes, "proportion": 0.25},
)
print(grapes_modification.text)

# This next one should fail because only one record can be attached for a crop/model_run combo. If you need to change it, patch the existing one.
grapes_modification_SHOULD_FAIL = requests.post(
    "http://localhost:8000/api/modification/",
    headers=auth_header,
    data={"model_run": model_run_id, "crop": grapes, "proportion": 0.2},
)
print(grapes_modification_SHOULD_FAIL)

# This one should fail because the user isn't authorized to attach modifications to model runs that aren't theirs
grapes_modification_AUTH_FAIL = requests.post(
    "http://localhost:8000/api/modification/",
    headers=auth_header,
    data={"model_run": 2, "crop": grapes, "proportion": 0.2},
)
print(grapes_modification_AUTH_FAIL)

set_ready = requests.patch(
    "http://localhost:8000/api/model_run/{}/".format(model_run_id),
    headers=auth_header,
    data={"ready": 1},
)
print(set_ready.text)

# Now check for results occasionally
results = None
while not results:
    time.sleep(2)
    print("Checking for results")
    model_info = requests.get(
        "http://localhost:8000/api/model_run/{}/".format(model_run_id),
        headers=auth_header,
    )
    if model_info.json()["complete"] is True:
        results = model_info.json()["result_values"]
        print("Got results!")
        print(results)
    else:
        print("No results yet. Ctrl-C to cancel checking and quit.")
