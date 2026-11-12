"""Budget kill switch: disables billing on the project when the budget is reached.

Cloud Billing budgets only send alerts; they never stop spending. This function
subscribes to the budget's Pub/Sub notifications and, once the reported cost
reaches the budget amount, unlinks the project from its billing account.
Everything billable in the project then stops (Cloud Run, Cloud SQL, Vertex AI
calls). To resume, re-link billing in the console.

The budget is set to exclude credits, so it counts the gross cost of usage
even while the free trial credit pays for it.

Note: budget notifications arrive with a delay (often hours), so spending can
overshoot the cap slightly before this runs.
"""

import base64
import json
import os

import functions_framework
from googleapiclient import discovery

PROJECT_ID = os.environ["PROJECT_ID"]


@functions_framework.cloud_event
def stop_billing(cloud_event) -> None:
    payload = json.loads(base64.b64decode(cloud_event.data["message"]["data"]).decode())
    cost = float(payload.get("costAmount", 0))
    budget = float(payload.get("budgetAmount", 0))
    print(json.dumps({"message": "budget notification", "cost": cost, "budget": budget}))
    if budget <= 0 or cost < budget:
        return

    billing = discovery.build("cloudbilling", "v1", cache_discovery=False)
    name = f"projects/{PROJECT_ID}"
    info = billing.projects().getBillingInfo(name=name).execute()
    if not info.get("billingEnabled"):
        print(json.dumps({"message": "billing already disabled"}))
        return
    billing.projects().updateBillingInfo(name=name, body={"billingAccountName": ""}).execute()
    print(json.dumps({"severity": "WARNING", "message": "billing disabled: budget reached",
                      "cost": cost, "budget": budget}))
