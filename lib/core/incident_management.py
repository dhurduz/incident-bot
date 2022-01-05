import logging
import os
import re

from dotenv import load_dotenv
from slack import errors
from typing import Dict

from . import slack_tools
from ..incident import incident
from ..db import db
from ..shared import tools

from . import action_parameters as ap

logger = logging.getLogger(__name__)

# .env parse
dotenv_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
)
load_dotenv(dotenv_path)

log_level = os.getenv("BOT_LOG_LEVEL")


def database_read(action_parameters: type[ap.ActionParameters]) -> Dict[str, str]:
    """Reads database data regarding an incident so values can be used
    index 3 is boilerplate message timestamp
    index 4 is digest message timestamp
    """
    p = action_parameters.parameters()
    database_data = db.db_read_incident(p["channel_name"])
    return {
        "bp_message_ts": database_data[5],
        "dig_message_ts": database_data[6],
    }


def assign_role(action_parameters: type[ap.ActionParameters]):
    """When an incoming action is incident.assign_role, this method
    assigns the role to the user provided in the input
    """
    p = action_parameters.parameters()
    channel_name = p["channel_name"]

    user = action_parameters.actions()["selected_user"]
    action_value = "_".join(action_parameters.actions()["block_id"].split("_")[1:3])
    # Find the index of the block that contains info on
    # the role we want to update
    blocks = action_parameters.message_details()["blocks"]
    index = tools.find_index_in_list(blocks, "block_id", f"role_{action_value}")
    # Replace the "_none_" value in the given block
    temp_new_role_name = action_value.replace("_", " ")
    new_role_name = temp_new_role_name.title()
    blocks[index]["text"]["text"] = f"*{new_role_name}*:\n <@{user}>"
    # Update the message
    slack_tools.slack_web_client.chat_update(
        channel=p["channel_id"],
        ts=p["timestamp"],
        blocks=blocks,
    )
    # Send update notification message to incident channel
    message = incident.build_role_update(p["channel_id"], new_role_name, user)
    try:
        result = slack_tools.slack_web_client.chat_postMessage(**message)
        if log_level == "DEBUG":
            logger.debug(f"\n{result}\n")
    except errors.SlackApiError as error:
        logger.error(f"Error sending role update to the incident channel: {error}")
    # Let the user know they've been assigned the role and what to do
    dm = incident.build_user_role_notification(p["channel_id"], action_value, user)
    try:
        result = slack_tools.slack_web_client.chat_postMessage(**dm)
        if log_level == "DEBUG":
            logger.debug(f"\n{result}\n")
    except errors.SlackApiError as error:
        logger.error(f"Error sending role description to user: {error}")
    logger.info(f"{user} was assigned {action_value} in {channel_name}")


def claim_role(action_parameters: type[ap.ActionParameters]):
    """When an incoming action is incident.claim_role, this method
    assigns the role to the user that hit the claim button
    """
    p = action_parameters.parameters()
    channel_name = p["channel_name"]

    action_value = action_parameters.actions()["value"]
    # Find the index of the block that contains info on
    # the role we want to update
    blocks = action_parameters.message_details()["blocks"]
    index = tools.find_index_in_list(blocks, "block_id", f"role_{action_value}")
    # Replace the "_none_" value in the given block
    temp_new_role_name = action_value.replace("_", " ")
    new_role_name = temp_new_role_name.title()
    user = p["user"]
    blocks[index]["text"]["text"] = f"*{new_role_name}*:\n <@{user}>"
    # Update the message
    slack_tools.slack_web_client.chat_update(
        channel=p["channel_id"],
        ts=p["timestamp"],
        blocks=blocks,
    )
    # Send update notification message to incident channel
    message = incident.build_role_update(p["channel_id"], new_role_name, user)
    try:
        result = slack_tools.slack_web_client.chat_postMessage(**message)
        logger.debug(f"\n{result}\n")
    except errors.SlackApiError as error:
        logger.error(f"Error sending role update to incident channel: {error}")
    # Let the user know they've been assigned the role and what to do
    dm = incident.build_user_role_notification(
        p["channel_id"],
        action_value,
        action_parameters.user_details()["id"],
    )
    try:
        result = slack_tools.slack_web_client.chat_postMessage(**dm)
        logger.debug(f"\n{result}\n")
    except errors.SlackApiError as error:
        logger.error(f"Error sending role description to user: {error}")
    logger.info(f"{user} has claimed {action_value} in {channel_name}")


def set_incident_status(action_parameters: type[ap.ActionParameters]):
    """When an incoming action is incident.set_incident_status, this method
    updates the status of the incident
    """
    p = action_parameters.parameters()
    channel_name = p["channel_name"]

    channel_id = p["channel_id"]
    database_query_values = database_read(action_parameters=action_parameters)

    action_value = action_parameters.actions()["selected_option"]["value"]
    message = incident.build_status_update(channel_id, action_value)
    try:
        result = slack_tools.slack_web_client.chat_postMessage(**message)
        logger.debug(f"\n{result}\n")
    except errors.SlackApiError as error:
        logger.error(
            f"Error sending status update to incident channel {channel_name}: {error}"
        )
    # Log
    logger.info(f"Updated incident status for {channel_name} to {action_value}.")
    # If set to resolved, send additional information.
    if action_value == "resolved":
        message = incident.build_post_resolution_message(channel_id, action_value)
        try:
            result = slack_tools.slack_web_client.chat_postMessage(**message)
            logger.debug(f"\n{result}\n")
        except errors.SlackApiError as error:
            logger.error(
                f"Error sending resolution update to incident channel {channel_name}: {error}"
            )
        # Log
        logger.info(f"Sent resolution info to {channel_name}.")
    # Also updates digest message
    channels = slack_tools.return_slack_channel_info()
    index = tools.find_index_in_list(channels, "name", incident.digest_channel)
    digest_channel_id = channels[index]["id"]
    # Retrieve the existing value of severity since we need to put that back
    try:
        result = slack_tools.slack_web_client.conversations_history(
            channel=digest_channel_id,
            inclusive=True,
            oldest=database_query_values["dig_message_ts"],
            limit=1,
        )
        message = result["messages"][0]
        severity_block_index = tools.find_index_in_list(
            message["blocks"], "block_id", "digest_channel_severity"
        )
        current_severity = message["blocks"][severity_block_index]["text"]["text"]
        regex = "\*(.*?)\*"
        formatted_severity = (
            re.search(regex, current_severity).group(1).replace("*", "").lower()
        )
    except errors.SlackApiError as e:
        logger.error(
            f"Error retrieving current severity from digest message for {channel_name}: {error}"
        )
    new_digest_message = incident.build_updated_digest_message(
        p["channel_name"], action_value, formatted_severity
    )
    try:
        slack_tools.slack_web_client.chat_update(
            channel=digest_channel_id,
            ts=database_query_values["dig_message_ts"],
            blocks=new_digest_message["blocks"],
        )
    except errors.SlackApiError as e:
        logger.error(
            f"Error sending status update to incident channel {channel_name}: {error}"
        )
    # Update incident record with the status
    logger.info(
        f"Updating incident record in database with new status for {channel_name}"
    )
    try:
        db.db_update_incident_status_col(
            channel_name,
            action_value,
        )
    except Exception as error:
        logger.fatal(f"Error updating entry in database: {error}")


def set_severity(action_parameters: type[ap.ActionParameters]):
    """When an incoming action is incident.set_severity, this method
    updates the severity of the incident
    """
    p = action_parameters.parameters()
    channel_name = p["channel_name"]

    channel_id = p["channel_id"]
    database_query_values = database_read(action_parameters=action_parameters)

    action_value = action_parameters.actions()["selected_option"]["value"]
    message = incident.build_severity_update(
        channel_id, action_value
    )  # build severity update
    try:
        result = slack_tools.slack_web_client.chat_postMessage(**message)
        logger.debug(f"\n{result}\n")
    except errors.SlackApiError as error:
        logger.error(
            f"Error sending severity update to incident channel {channel_name}: {error}"
        )
    # Log
    logger.info(f"Updated incident severity for {channel_name} to {action_value}.")
    # Also updates digest message
    channels = slack_tools.return_slack_channel_info()
    index = tools.find_index_in_list(channels, "name", incident.digest_channel)
    digest_channel_id = channels[index]["id"]
    # Retrieve the existing value of status since we need to put that back
    try:
        result = slack_tools.slack_web_client.conversations_history(
            channel=digest_channel_id,
            inclusive=True,
            oldest=database_query_values["dig_message_ts"],
            limit=1,
        )
        message = result["messages"][0]
        status_block_index = tools.find_index_in_list(
            message["blocks"], "block_id", "digest_channel_status"
        )
        current_status = message["blocks"][status_block_index]["text"]["text"]
        regex = "\*(.*?)\*"
        formatted_status = (
            re.search(regex, current_status).group(1).replace("*", "").lower()
        )
    except errors.SlackApiError as error:
        logger.error(f"Error retrieving current status for {channel_name}: {error}")
    new_digest_message = incident.build_updated_digest_message(
        p["channel_name"], formatted_status, action_value
    )
    try:
        slack_tools.slack_web_client.chat_update(
            channel=digest_channel_id,
            ts=database_query_values["dig_message_ts"],
            blocks=new_digest_message["blocks"],
        )
    except errors.SlackApiError as error:
        logger.error(
            f"Error sending severity update to incident channel {channel_name}: {error}"
        )
    # Update incident record with the severity
    logger.info(
        f"Updating incident record in database with new severity for {channel_name}"
    )
    try:
        db.db_update_incident_severity_col(
            channel_name,
            action_value,
        )
    except Exception as error:
        logger.fatal(f"Error updating entry in database: {error}")