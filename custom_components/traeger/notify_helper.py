"""Notification Helper for Traeger."""

import logging

from homeassistant.util import slugify

_LOGGER: logging.Logger = logging.getLogger(__package__)

def notifydevices(title, msg, notify, hass):
    """Central Notify Func"""
    data = {
        "title": title,
        "message": msg,
    }
    _LOGGER.error("MSG Base Data: %s", data)
    for notidev in notify:
        if "name" in notify[notidev]:
            _LOGGER.error("NotiDev Info: %s - %s", notify[notidev]["name"], notify[notidev]["manu"])
            hass.async_create_task(
                hass.services.async_call(
                    "notify",
                    slugify(f"mobile_app_{notify[notidev]["name"]}"),
                    data, False)
            )
