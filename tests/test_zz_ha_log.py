"""Tests to check HA Logs."""

import logging

import pytest
from aiointercept import aiointercept
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.traeger.const import DOMAIN

from .zzcommon import CallbackAPI, client_connect, client_disconnect
from .zzMockResp import api_user_self

_LOGGER: logging.Logger = logging.getLogger(__package__)


@pytest.mark.usefixtures("socket_enabled")
async def test_zz_ha_log(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    http: aiointercept,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test HA Logs"""
    # pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments

    traeger_client = hass.data[DOMAIN][mock_config_entry.entry_id]
    CallbackAPI(traeger_client, http)
    await client_connect(hass, traeger_client, api_user_self["resp"]["things"])

    # Check a known log exists.
    assert any("Was at callbacks" in record.message for record in caplog.records)

    # Check if we have used any deprec items
    assert not any(
        "Detected that custom integration 'traeger'" in record.message
        for record in caplog.records
    )

    await client_disconnect(hass, traeger_client)
