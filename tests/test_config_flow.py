"""Test the Traeger Client."""

import asyncio
import logging

import pytest
from aiointercept import aiointercept
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.traeger.const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

from .zzMockResp import api_token, api_mqtt, api_user_self

_LOGGER: logging.Logger = logging.getLogger(__package__)


# TestTraegerConfigFlow
# pylint: disable=unused-argument
async def test_config_flow_show_user_form(
    hass: HomeAssistant, http: aiointercept
) -> None:
    """Test that user form is shown on init."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    _LOGGER.info("Config Flow Result Show: %s", result)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

# pylint: disable=unused-argument
async def test_config_flow_success(hass: HomeAssistant, http: aiointercept) -> None:
    """Test Success User Flow with Ent Create"""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Submit credentials
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "johnytraeger@traeger.com",
            CONF_PASSWORD: "johnytraeger'spassword",
        },
    )

    _LOGGER.info("Config Flow Result Success: %s", result)
    # Flow Result is created entity
    assert result["type"] == FlowResultType.CREATE_ENTRY


# pylint: disable=too-many-arguments,too-many-positional-arguments
@pytest.mark.parametrize(
    "p_api_token, p_api_user_self, p_api_mqtt, assert1, assert2",
    [
        (
            {
                "payload": api_token["resp"],
                "status": 400,
            },
            {
                "payload": api_user_self["resp"],
                "status": 400,
            },
            {
                "payload": api_mqtt["resp"],
                "status": 400,
            },
            FlowResultType.CREATE_ENTRY,
            None,
        ),
        (
            {
                "payload": {"error": "badtoken"},
                "status": 400,
            },
            {
                "payload": api_user_self["resp"],
                "status": 400,
            },
            {
                "payload": api_mqtt["resp"],
                "status": 400,
            },
            FlowResultType.FORM,
            {"base": "auth"},
        ),
        (
            {
                "payload": api_token["resp"],
                "status": 400,
            },
            {
                "payload": {"error": "baduser"},
                "status": 400,
            },
            {
                "payload": api_mqtt["resp"],
                "status": 400,
            },
            FlowResultType.FORM,
            {"base": "auth"},
        ),
    ],
)
async def test_config_flow_fail(
    p_api_token,
    p_api_user_self,
    p_api_mqtt,
    assert1,
    assert2,
    hass: HomeAssistant,
    http: aiointercept,
) -> None:
    """Test Failed User Flow"""
    http.clear()
    http.post(
        api_token["url"],
        payload=p_api_token["payload"],
        status=p_api_token["status"],
        repeat=True,
    )
    http.get(
        api_user_self["url"],
        payload=p_api_user_self["payload"],
        status=p_api_user_self["status"],
        repeat=True,
    )
    http.post(
        api_mqtt["url"],
        payload=p_api_mqtt["payload"],
        status=p_api_mqtt["status"],
        repeat=True,
    )

    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Submit credentials
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_USERNAME: "johnytraeger@traeger.com",
            CONF_PASSWORD: "johnytraeger'spassword",
        },
    )

    _LOGGER.info("Config Flow Result Fail: %s", result)
    # Flow Result is failed
    assert result["type"] == assert1
    assert assert2 is None or result["errors"] == assert2
