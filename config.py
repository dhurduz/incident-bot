import logging
import os
from dotenv import load_dotenv

# .env parse
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)
log_level = os.getenv("LOGLEVEL", "INFO").upper()

# Create the logging object
# This is used by submodules as well
logger = logging.getLogger(__name__)


"""
Global Variables
"""
templates_directory = os.getenv("TEMPLATES_DIRECTORY", default="templates/")


"""
Database Settings
"""
database_host = os.getenv("DATABASE_HOST")
database_name = os.getenv("DATABASE_NAME")
database_password = os.getenv("DATABASE_PASSWORD")
database_port = os.getenv("DATABASE_PORT")
database_user = os.getenv("DATABASE_USER")


"""
Incidents Module
"""
incidents_digest_channel = os.getenv("INCIDENTS_DIGEST_CHANNEL")
slack_workspace_id = os.getenv("SLACK_WORKSPACE_ID")

## Options
incident_auto_create_from_react_enabled = os.getenv(
    "INCIDENT_AUTO_CREATE_FROM_REACT_ENABLED", default="false"
)
incident_auto_create_from_react_emoji_name = os.getenv(
    "INCIDENT_AUTO_CREATE_FROM_REACT_EMOJI_NAME", default=""
)
incident_auto_group_invite_enabled = os.getenv(
    "INCIDENT_AUTO_GROUP_INVITE_ENABLED", default="false"
)
incident_auto_group_invite_group_name = os.getenv(
    "INCIDENT_AUTO_GROUP_INVITE_GROUP_NAME", default=""
)
incident_external_providers_enabled = os.getenv(
    "INCIDENT_EXTERNAL_PROVIDERS_ENABLED", default="false"
)
incident_external_providers_list = os.getenv(
    "INCIDENT_EXTERNAL_PROVIDERS_LIST", default="false"
)
incident_channel_topic = os.getenv("INCIDENT_CHANNEL_TOPIC")
incident_guide_link = os.getenv("INCIDENT_GUIDE_LINK")
incident_postmortems_link = os.getenv("INCIDENT_POSTMORTEMS_LINK")


"""
Slack
"""
slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
slack_verification_token = os.getenv("SLACK_VERIFICATION_TOKEN")


"""
Statuspage Module
"""
statuspage_api_key = os.getenv("STATUSPAGE_API_KEY", default="")
statuspage_integration_enabled = os.getenv(
    "STATUSPAGE_INTEGRATION_ENABLED", default="false"
)
statuspage_page_id = os.getenv("STATUSPAGE_PAGE_ID", default="")
statuspage_url = os.getenv("STATUSPAGE_URL", default="")


"""
External
"""
auth0_domain = os.getenv("AUTH0_DOMAIN", default="")


"""
Helper Methods
"""


def env_check(envs):
    logger.info("Running env check...")
    for e in envs:
        if os.getenv(e) == "":
            logger.fatal(f"The environment variable {e} cannot be empty.")
            exit(1)
        else:
            pass
    if incident_auto_create_from_react_enabled == "true":
        if incident_auto_create_from_react_emoji_name == "":
            logger.fatal(
                f"If enabling auto create via react, the INCIDENT_AUTO_CREATE_FROM_REACT_EMOJI_NAME variable must be set."
            )
            exit(1)
    if incident_auto_group_invite_enabled == "true":
        if incident_auto_group_invite_group_name == "":
            logger.fatal(
                f"If enabling auto group invite, the INCIDENT_AUTO_GROUP_INVITE_GROUP_NAME variable must be set."
            )
            exit(1)
    if incident_external_providers_enabled == "true":
        if "auth0" in incident_external_providers_list:
            if auth0_domain == "":
                logger.fatal(
                    f"If enabling Auth0 status updates via external providers, you must set AUTH0_DOMAIN."
                )
                exit(1)
    if statuspage_integration_enabled == "true":
        for var in ["STATUSPAGE_API_KEY", "STATUSPAGE_PAGE_ID", "STATUSPAGE_URL"]:
            if os.getenv(var) == "":
                logger.fatal(
                    f"If enabling the Statuspage integration, the {var} variable must be set."
                )
                exit(1)