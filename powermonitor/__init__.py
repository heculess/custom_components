"""Support for PowerMonito devices."""
import logging

import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.const import CONF_NAME

_LOGGER = logging.getLogger(__name__)

CONF_GROUP_ID = 'group_id'
CONF_POWER_KEY = 'power_key'
CONF_MAX_POWER = 'max_power'
CONF_MAX_POWER_CONF = 'max_power_config'

DOMAIN = "powermonitor"
DATA_POWERMON = DOMAIN
DEFAULT_POWER_KEY = "load_power"
DEFAULT_MAX_POWER = 4800

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_GROUP_ID): cv.string,
                vol.Optional(CONF_POWER_KEY,default=DEFAULT_POWER_KEY): cv.string,
                vol.Optional(CONF_MAX_POWER ,default=DEFAULT_MAX_POWER): cv.positive_int,
                vol.Optional(CONF_MAX_POWER_CONF,default=""): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class PowerMonitor:
    """interface of a power monitor."""

    def __init__(self, group_id, power_key, max_power, max_power_conf, conf_name):
        """Init function."""
        self._group_id = group_id
        self._power_key = power_key
        self._max_power = max_power
        self._max_power_conf = max_power_conf
        self._name = conf_name

    @property
    def name(self):
        """Return the name of the PowerMonito."""
        return self._name

    @property
    def group_id(self):
        """Return the name of the PowerMonito."""
        return self._group_id

    @property
    def power_key(self):
        """Return the name of the PowerMonito."""
        return self._power_key

    @property
    def max_power(self):
        """Return the name of the PowerMonito."""
        return self._max_power

    @property
    def max_power_conf(self):
        """Return the name of the PowerMonito."""
        return self._max_power_conf


async def async_setup(hass, config):
    """Set up the asusrouter component."""

    conf = []

    if DOMAIN in config:
        conf = config[DOMAIN]

        hass.data[DATA_POWERMON] = PowerMonitor(
            conf[CONF_GROUP_ID],
            conf[CONF_POWER_KEY],
            conf[CONF_MAX_POWER],
            conf[CONF_MAX_POWER_CONF],
            conf[CONF_NAME]
        )

    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )
    

    return True
          
