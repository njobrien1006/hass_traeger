"""Notification Helper for Traeger."""

import logging

from homeassistant.util import slugify

_LOGGER: logging.Logger = logging.getLogger(__package__)


def notifydevices(
    notify,
    hass,
    *,
    title,
    msg,
):
    """Central Notify Func"""
    data = {
        "title": title,
        "message": msg,
    }
    _LOGGER.info("MSG Base Data: %s", data)
    for notidev in notify:
        if notify[notidev] is not None and "name" in notify[notidev]:
            _LOGGER.info(
                "NotiDev Info: %s - %s",
                notify[notidev]["name"],
                notify[notidev]["manu"],
            )
            hass.async_create_task(
                hass.services.async_call(
                    "notify",
                    slugify(f"mobile_app_{notify[notidev]['name']}"),
                    data,
                    False,
                )
            )


# pylint: disable=too-many-arguments
def notifystartliveupdate_time(notify, hass, *, tag, title, msg, unix):
    """Start Live Update Chrono"""
    data = {
        "title": title,
        "message": msg,
        "data": {"tag": tag, "live_update": True, "chronometer": True, "when": unix},
    }
    _LOGGER.info("MSG Base Data: %s", data)
    for notidev in notify:
        if notify[notidev] is not None and "name" in notify[notidev]:
            _LOGGER.info(
                "NotiDev Info: %s - %s",
                notify[notidev]["name"],
                notify[notidev]["manu"],
            )
            hass.async_create_task(
                hass.services.async_call(
                    "notify",
                    slugify(f"mobile_app_{notify[notidev]['name']}"),
                    data,
                    False,
                )
            )


def notifyclearliveupdate(notify, hass, *, tag):
    """Clear Live Update Chrono"""
    data = {"message": "clear_notification", "data": {"tag": tag}}
    _LOGGER.info("MSG Base Data: %s", data)
    for notidev in notify:
        if notify[notidev] is not None and "name" in notify[notidev]:
            _LOGGER.info(
                "NotiDev Info: %s - %s",
                notify[notidev]["name"],
                notify[notidev]["manu"],
            )
            hass.async_create_task(
                hass.services.async_call(
                    "notify",
                    slugify(f"mobile_app_{notify[notidev]['name']}"),
                    data,
                    False,
                )
            )
