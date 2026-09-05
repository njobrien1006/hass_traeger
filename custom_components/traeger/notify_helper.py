"""Notification Helper for Traeger."""

import copy
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
    data = {"title": title, "message": msg, "data": {}}
    _LOGGER.info("MSG Base Data: %s", data)
    for notidev in notify:
        if notify[notidev] is not None and "name" in notify[notidev]:
            noti_data = copy.deepcopy(data)
            if notify[notidev]["manu"] == "Apple":
                noti_data["data"].update({"url": "/lovelace/grill"})
            else:
                noti_data["data"].update({"clickAction": "/lovelace/grill"})
            _LOGGER.info(
                "NotiDev Info: %s - %s\n%s",
                notify[notidev]["name"],
                notify[notidev]["manu"],
                noti_data,
            )
            hass.async_create_task(
                hass.services.async_call(
                    "notify",
                    slugify(f"mobile_app_{notify[notidev]['name']}"),
                    noti_data,
                    False,
                )
            )


# pylint: disable=too-many-arguments
def notifystartliveupdate_time(notify, hass, *, tag, title, msg, unix, icon):
    """Start Live Update Chrono"""
    data = {
        "title": title,
        "message": msg,
        "data": {
            "tag": tag,
            "live_update": True,
            "chronometer": True,
            "notification_icon": icon,
            "when": unix,
        },
    }
    _LOGGER.info("MSG Base Data: %s", data)
    for notidev in notify:
        if notify[notidev] is not None and "name" in notify[notidev]:
            noti_data = copy.deepcopy(data)
            if notify[notidev]["manu"] == "Apple":
                noti_data["data"].update(
                    {"url": "/lovelace/grill", "notification_icon_color": "#FF7900"}
                )
            else:
                noti_data["data"].update(
                    {"clickAction": "/lovelace/grill", "color": "#FF7900"}
                )
            _LOGGER.info(
                "NotiDev Info: %s - %s\n%s",
                notify[notidev]["name"],
                notify[notidev]["manu"],
                noti_data,
            )
            hass.async_create_task(
                hass.services.async_call(
                    "notify",
                    slugify(f"mobile_app_{notify[notidev]['name']}"),
                    noti_data,
                    False,
                )
            )


# pylint: disable=too-many-arguments
def notifyliveupdate_text(
    notify, hass, *, tag, title, msg, icon, icon_color="#FF7900", silent=True
):
    """Live Update Text Only"""
    data = {
        "title": title,
        "message": msg.replace("\n", chr(10)),
        "data": {
            "tag": tag,
            "live_update": True,
            "notification_icon": icon,
        },
    }
    _LOGGER.info("MSG Base Data: %s", data)
    for notidev in notify:
        if notify[notidev] is not None and "name" in notify[notidev]:
            noti_data = copy.deepcopy(data)
            if notify[notidev]["manu"] == "Apple":
                noti_data["data"].update(
                    {
                        "url": "/lovelace/grill",
                        "notification_icon_color": icon_color,
                        "silent": silent,
                    }
                )
            else:
                noti_data["data"].update(
                    {
                        "clickAction": "/lovelace/grill",
                        "color": icon_color,
                        "alert_once": silent,
                    }
                )
            _LOGGER.info(
                "NotiDev Info: %s - %s\n%s",
                notify[notidev]["name"],
                notify[notidev]["manu"],
                noti_data,
            )
            hass.async_create_task(
                hass.services.async_call(
                    "notify",
                    slugify(f"mobile_app_{notify[notidev]['name']}"),
                    noti_data,
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
