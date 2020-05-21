"""Support for SwitchMonitor devices."""
import logging
import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
)

_LOGGER = logging.getLogger(__name__)

CONF_GROUP_ID = 'group_id'

DOMAIN = "devicescounter"
DATA_DEVICESCOUNTER = DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_GROUP_ID): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

class DevicesCounter:
    """interface of a power monitor."""

    def __init__(self, group_id, conf_name):
        """Init function."""
        self._group_id = group_id
        self._name = conf_name

    @property
    def name(self):
        """Return the name of the SwitchMonitor."""
        return self._name

    @property
    def group_id(self):
        """Return the name of the SwitchMonitor."""
        return self._group_id


async def async_setup(hass, config):
    """Set up the asusrouter component."""

    conf = []

    if DOMAIN in config:
        conf = config[DOMAIN]

        hass.data[DATA_DEVICESCOUNTER] = DevicesCounter(
            conf[CONF_GROUP_ID],
            conf[CONF_NAME]
        )

    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    return True

