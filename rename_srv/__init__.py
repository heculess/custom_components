"""Support for Rename Service."""
import logging
import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from .http import RenameGateway

_LOGGER = logging.getLogger(__name__)


DOMAIN = "rename_srv"
DOMAIN_SRV = DOMAIN
CONF_SERVER_ID = 'server_id'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_SERVER_ID): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):

    if DOMAIN in config:
        server_conf = config[DOMAIN]

    http_gateway = RenameGateway(hass, server_conf[CONF_SERVER_ID])
    hass.data[DOMAIN_SRV] = http_gateway

    await http_gateway.register_gateway()

    hass.async_create_task(
        async_load_platform(hass, "switch", DOMAIN, {}, config)
    )

    return True



          
