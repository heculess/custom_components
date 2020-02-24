"""Support for ALIDDNS devices."""
import logging

import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.const import CONF_NAME

_LOGGER = logging.getLogger(__name__)

CONF_ACCESS_ID = 'access_id'
CONF_ACCESS_KEY = 'access_key'
CONF_DOMAIN = 'domain'
CONF_SUB_DOMAIN = 'sub_domain'

DOMAIN = "aliddns"
DATA_ALIDDNS = DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_ACCESS_ID): cv.string,
                vol.Required(CONF_ACCESS_KEY): cv.string,
                vol.Required(CONF_DOMAIN): cv.string,
                vol.Required(CONF_SUB_DOMAIN): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class AliddnsConfig:
    """interface of a asusrouter."""

    def __init__(self, access_id, access_key, domain, sub_domain, conf_name):
        """Init function."""
        self._access_id = access_id
        self._access_key = access_key
        self._domain = domain
        self._sub_domain = sub_domain
        self._name = conf_name

    @property
    def name(self):
        """Return the name of the ddns."""
        return self._name

    @property
    def domain(self):
        """Return the name of the ddns."""
        return self._domain

    @property
    def sub_domain(self):
        """Return the name of the ddns."""
        return self._sub_domain

    @property
    def access_id(self):
        """Return the name of the ddns."""
        return self._access_id

    @property
    def access_key(self):
        """Return the name of the ddns."""
        return self._access_key


async def async_setup(hass, config):
    """Set up the asusrouter component."""

    conf = []

    if DOMAIN in config:
        conf = config[DOMAIN]

        hass.data[DATA_ALIDDNS] = AliddnsConfig(
            conf[CONF_ACCESS_ID],
            conf[CONF_ACCESS_KEY],
            conf[CONF_DOMAIN],
            conf[CONF_SUB_DOMAIN],
            conf[CONF_NAME]
        )

    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )
    

    return True
          
