"""Test the Traeger Client."""

import logging
from aioresponses import aioresponses

from .conftest import TraegerTestClient
from .zzMockResp import api_commands, api_token, api_mqtt, api_user_self

_LOGGER: logging.Logger = logging.getLogger(__package__)


#TestTraegerClient
async def test_handle_tokens(traeger_client: TraegerTestClient,
                             http: aioresponses) -> None:
    """test getting token"""
    http.post(api_token['url'], payload=api_token['resp'])
    traeger_client.api['username'] = "JohnyTraeger@traeger.com"
    traeger_client.api['password'] = "abc123"
    response = await traeger_client.do_cognito()
    _LOGGER.warning("do cognito resp: %s", response)
    assert response.get("idToken", None) not in [None, ""]
    assert response.get("expiresIn", None) not in [None, ""]


async def test_handle_tokens_bad_user_pass(traeger_client: TraegerTestClient,
                                           http: aioresponses) -> None:
    """test getting token with bad PAR"""
    http.post(api_token['url'], payload={'error': 'badpass'})
    traeger_client.api['username'] = ""
    traeger_client.api['password'] = ""
    response = await traeger_client.do_cognito()
    _LOGGER.warning("do cognito resp: %s", response)


async def test_handle_user(traeger_client: TraegerTestClient,
                           http: aioresponses) -> None:
    """test getting user data"""
    http.post(api_token['url'], payload=api_token['resp'])
    http.get(api_user_self['url'], payload=api_user_self['resp'])
    traeger_client.api['username'] = "JohnyTraeger@traeger.com"
    traeger_client.api['password'] = "abc123"
    response = await traeger_client.get_user_data()
    _LOGGER.warning("do cognito resp: %s", response)
    assert response.get("username", None) not in [None, ""]
    assert response.get("things", None) not in [None, ""]


async def test_handle_user_bad(traeger_client: TraegerTestClient,
                               http: aioresponses) -> None:
    """test getting user data with bad data"""
    http.post(api_token['url'], payload={'error': 'badpass'})
    http.get(api_user_self['url'], payload={'error': 'badtoken'})
    traeger_client.api['username'] = ""
    traeger_client.api['password'] = ""
    response = await traeger_client.get_user_data()
    _LOGGER.warning("do cognito resp: %s", response)


async def test_handle_mqtturl(traeger_client: TraegerTestClient,
                              http: aioresponses) -> None:
    """test getting mqtt url"""
    http.post(api_token['url'], payload=api_token['resp'])
    http.post(api_mqtt['url'], payload=api_mqtt['resp'])
    traeger_client.api['username'] = "JohnyTraeger@traeger.com"
    traeger_client.api['password'] = "abc123"
    response = await traeger_client.refresh_mqtt_url()
    _LOGGER.warning("do cognito resp: %s", response)
    assert traeger_client.api['mqtt_url_expires'] not in [None, "", 0]
    assert traeger_client.api['mqtt_url'] not in [None, "", 0]


async def test_handle_mqtturl_bad(traeger_client: TraegerTestClient,
                                  http: aioresponses) -> None:
    """test getting mqtt url bad"""
    http.post(api_token['url'], payload={'error': 'badpass'})
    http.post(api_mqtt['url'], payload={'error': 'badtoken'})
    traeger_client.api['username'] = ""
    traeger_client.api['password'] = ""
    response = await traeger_client.refresh_mqtt_url()
    _LOGGER.warning("do cognito resp: %s", response)


async def test_handle_cmd(traeger_client: TraegerTestClient,
                          http: aioresponses) -> None:
    """test grill command"""
    http.post(api_token['url'], payload=api_token['resp'])
    http.post(api_commands['url'], payload=api_commands['resp'])
    traeger_client.api['username'] = "JohnyTraeger@traeger.com"
    traeger_client.api['password'] = "abc123"
    response = await traeger_client.update_state("0123456789ab")
    _LOGGER.warning("do cognito resp: %s", response)
    assert True


async def test_handle_cmd_bad(traeger_client: TraegerTestClient,
                              http: aioresponses) -> None:
    """test grill command"""
    http.post(api_token['url'], payload={'error': 'badpass'})
    http.post(api_commands['url'], payload={'error': 'badtoken'})
    traeger_client.api['username'] = "JohnyTraeger@traeger.com"
    traeger_client.api['password'] = None
    await traeger_client.update_state("0123456789ab")
    assert True
