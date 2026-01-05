import random

import pytest
from homeassistant.core import HomeAssistant
from paho.mqtt.client import MQTTMessage

from .conftest import TraegerTestClient


class TestMessageParsing:
    
    def test_handle_unknown_messages(self, Traeger_client: TraegerTestClient) -> None:
        message = MQTTMessage(topic=b"unknown")
        message.payload = b"whatever"
        # Don't throw on this:
        Traeger_client._on_message(Traeger_client._mqtt_client, None, message)

    async def test_parse_state(self, Traeger_client: TraegerTestClient):
        assert Traeger_client.state.fan_mode is None

        await Traeger_client.apply_state_messages(
            {
                "status": "online",
                "fan": "2",
                "party": "0",
                "absent": "0",
                "textr": "18",
                "texauh": "19",
                "tsupl": "20",
                "tout": "21",
                "overheating": "22",
                "he": "1",
            }
        )

        assert Traeger_client.state == TraegerState(
            is_online=True,
            fan_mode=FanMode.MEDIUM,
            preset_mode=PresetMode.HOME,
            temperature_extract=18,
            temperature_exhaust=19,
            temperature_supply=20,
            temperature_outside=21,
            temperature_heater=22,
            is_heating=True,
        )

        await Traeger_client.apply_state_messages({"party": "1"})
        Traeger_client.state.preset_mode == "party"

        await Traeger_client.apply_state_messages({"party": "2"})
        Traeger_client.state.preset_mode == "home"


class TestStateChanging:
    def test_set_temperature(self, Traeger_client: TraegerTestClient) -> None:
        assert Traeger_client.state.temperature_target is None
        Traeger_client.set_target_temperature(20)
        last_message = Traeger_client.published_messages[-1]
        assert (
            last_message.topic == f"{Traeger_client._apply_state_topic_prefix}temperature"
        )
        assert last_message.payload == b"20"

    def test_set_invalid_temperature(self, Traeger_client: TraegerTestClient) -> None:
        for target_temperature in (MIN_TEMPERATURE - 1, MAX_TEMPERATURE + 1):
            with pytest.raises(ValueError, match="Temperature out of bounds"):
                Traeger_client.set_target_temperature(target_temperature)

    def test_set_fan_mode(self, Traeger_client: TraegerTestClient) -> None:
        Traeger_client.state.preset_mode == "home"
        Traeger_client.set_target_temperature(20)
        last_message = Traeger_client.published_messages[-1]
        assert (
            last_message.topic == f"{Traeger_client._apply_state_topic_prefix}temperature"
        )
        assert last_message.payload == b"20"

    def test_set_fan_mode_resetting_to_home_mode(
        self, Traeger_client: TraegerTestClient
    ) -> None:
        # Adjusting the fan speed should clear the away/boost mode:
        Traeger_client.state.preset_mode = random.choice(("boost", "away"))
        Traeger_client.set_fan_mode(FanMode.MEDIUM)

        absent_cleared = False
        party_cleared = False
        fan_mode_set = False

        for message in Traeger_client.published_messages:
            if message.topic.endswith("/fan") and message.payload == b"2":
                fan_mode_set = True
            elif message.topic.endswith("absent") and message.payload == b"0":
                absent_cleared = True
            elif message.topic.endswith("party") and message.payload == b"2":
                party_cleared = True

        assert all((absent_cleared, party_cleared, fan_mode_set))


class TestOnlineAndDiscoveredEvents:
    async def test_online_and_discovered_events(
        self, Traeger_client: TraegerTestClient, hass: HomeAssistant
    ) -> None:
        assert not (
            # Discovered is whether Traeger reports anything for the MAC
            Traeger_client.device_is_discovered.is_set()
            # Online is whether the reporting ventilation aggregate is online, not whether
            # this client is connected
            or Traeger_client.device_is_online.is_set()
        )

        await Traeger_client.apply_state_messages({"status": "online"})

        # Should be both considered online and discovered:
        assert (
            Traeger_client.device_is_discovered.is_set()
            # Online is whether the reporting ventilation aggregate is online, not whether
            # this client is connected
            and Traeger_client.device_is_online.is_set()
        )

        # Pretend to disconnect
        await Traeger_client.disconnect()
        # We should still be discovered, but not online:
        assert (
            Traeger_client.device_is_discovered.is_set()
            and not Traeger_client.device_is_online.is_set()
        )
