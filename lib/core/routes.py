import json
import logging
import os

from __main__ import app
from dotenv import load_dotenv
from flask import request
from typing import Dict
from ..statuspage import statuspage

from . import action_parameters as ap
from . import incident_management
from . import statuspage

logger = logging.getLogger(__name__)

# .env parse
dotenv_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
)
load_dotenv(dotenv_path)

log_level = os.getenv("BOT_LOG_LEVEL")


@app.route("/hooks/actions", methods=["POST"])
def actions():
    """Parse actions
    This endpoint accepts requests based on actions
    sent from Slack.
    """
    payload = request.form["payload"]
    params = ap.ActionParameters(payload=payload)

    """
    Handle requests
    """
    p = params.parameters()

    # Handle incident management actions
    if "incident" in p["action_id"]:
        if p["action_id"] == "incident.claim_role":
            incident_management.claim_role(action_parameters=params)
        elif p["action_id"] == "incident.assign_role":
            incident_management.assign_role(action_parameters=params)
        # Update incident status
        elif p["action_id"] == "incident.set_incident_status":
            incident_management.set_incident_status(action_parameters=params)
        elif p["action_id"] == "incident.set_severity":
            incident_management.set_severity(action_parameters=params)
    # Handle statuspage actions
    elif "statuspage" in p["action_id"]:
        # components_select only appears in the initial message and is used to create a statuspage incident
        if p["action_id"] == "statuspage.components_select":
            statuspage.components_select(action_parameters=params)
        elif p["action_id"] == "statuspage.update_status":
            statuspage.update_status(action_parameters=params)
    return "ok"


@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}