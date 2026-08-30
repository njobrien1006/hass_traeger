"""
www registration helper from https://github.com/AlexxIT/WebRTC and redacted
"""

import logging

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


# pylint: disable=import-outside-toplevel
async def register_static_path(hass: HomeAssistant, url_path: str, path: str):
    """Register Static Path with HA."""
    if (MAJOR_VERSION, MINOR_VERSION) >= (2024, 7):
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(url_path, path, True)]
        )
    else:
        hass.http.register_static_path(url_path, path)


async def init_resource(hass: HomeAssistant, url: str, ver: str) -> bool:
    """Add extra JS module for lovelace mode YAML and new lovelace resource
    for mode GUI. It's better to add extra JS for all modes, because it has
    random url to avoid problems with the cache. But chromecast don't support
    extra JS urls and can't load custom card.
    """
    lovelace = hass.data["lovelace"]
    resources: ResourceStorageCollection = (
        lovelace.resources if hasattr(lovelace, "resources") else lovelace["resources"]
    )

    # force load storage
    await resources.async_get_info()

    url2 = f"{url}?v={ver}"

    for item in resources.async_items():
        if not item.get("url", "").startswith(url):
            continue

        # no need to update
        if item["url"].endswith(ver):
            return False

        _LOGGER.debug("Update lovelace resource to: %s", url2)

        if isinstance(resources, ResourceStorageCollection):
            await resources.async_update_item(
                item["id"], {"res_type": "module", "url": url2}
            )
        else:
            # not the best solution, but what else can we do
            item["url"] = url2

        return True

    if isinstance(resources, ResourceStorageCollection):
        _LOGGER.debug("Add new lovelace resource: %s", url2)
        await resources.async_create_item({"res_type": "module", "url": url2})
    else:
        _LOGGER.debug("Add extra JS module: %s", url2)
        add_extra_js_url(hass, url2)

    return True


def call_service_set_number(hass, entity, value):
    '''sync set number'''
    hass.async_create_task(call_service_async_set_number(hass, entity, value))


async def call_service_async_set_number(hass, entity, value):
    '''async set number'''
    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": entity,
            "value": value,
        },
        False,
    )


def call_service_set_climate(hass, entity, value):
    '''sync set climate temp'''
    hass.async_create_task(call_service_async_set_climate(hass, entity, value))


async def call_service_async_set_climate(hass, entity, value):
    '''async set climate temp'''
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            "entity_id": entity,
            "temperature": value,
        },
        False,
    )


def call_service_set_climate_mode(hass, entity, mode):
    '''sync set climate mode'''
    hass.async_create_task(call_service_async_set_climate_mode(hass, entity, mode))


async def call_service_async_set_climate_mode(hass, entity, mode):
    '''async set climate mode'''
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {
            "entity_id": entity,
            "hvac_mode": mode,
        },
        False,
    )


def call_service_set_switch(hass, entity, mode):
    '''sync set switch'''
    hass.async_create_task(call_service_async_set_switch(hass, entity, mode))


async def call_service_async_set_switch(hass, entity, mode):
    '''async set switch'''
    if mode not in ["turn_off", "turn_on"]:
        if mode == 0:
            setmode = "turn_off"
        elif mode == 1:
            setmode = "turn_on"
        else:
            _LOGGER.error("Unknown Mode")
            return
    else:
        setmode = mode
    await hass.services.async_call(
        "switch",
        setmode,
        {
            "entity_id": entity,
        },
        False,
    )
