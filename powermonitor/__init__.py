"""Support for PowerMonitor devices."""
import logging

import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    CONF_NAME,
)


_LOGGER = logging.getLogger(__name__)

CONF_GROUP_ID = 'group_id'
CONF_POWER_KEY = 'power_key'
CONF_MAX_POWER = 'max_power'
CONF_MAX_POWER_CONF = 'max_power_config'
CONF_GROUPS = "groups"
CONF_AUTO_RESTART = 'auto_restart'
CONF_EXTRA_POWER_MONITOR = 'extra_power_monitor_group'

CONF_ID_LIST = 'id_list'

DOMAIN = "powermonitor"
DATA_POWERMON = DOMAIN
DEFAULT_POWER_KEY = "load_power"
DEFAULT_MAX_POWER = 4800

GROUP_CONFIG = vol.Schema(
    {
        vol.Required(CONF_GROUP_ID): cv.string,
        vol.Optional(CONF_POWER_KEY,default=DEFAULT_POWER_KEY): cv.string,
        vol.Optional(CONF_MAX_POWER ,default=DEFAULT_MAX_POWER): cv.positive_int,
        vol.Optional(CONF_MAX_POWER_CONF,default=""): cv.string,
        vol.Optional(CONF_AUTO_RESTART,default=True): cv.boolean,
        vol.Optional(CONF_EXTRA_POWER_MONITOR,default=""): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_GROUPS, default={}): vol.All(
                    cv.ensure_list,vol.All([GROUP_CONFIG]),
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


SERVICE_TURN_ALL_ON = "turn_all_on"
SERVICE_TURN_ALL_ON_SCHEMA = vol.Schema({vol.Required(CONF_ID_LIST): cv.string})

class PowerMonitor:
    """interface of a power monitor."""

    def __init__(self, group_id, power_key, max_power, max_power_conf):
        """Init function."""
        self._group_id = group_id
        self._power_key = power_key
        self._max_power = max_power
        self._max_power_conf = max_power_conf
        self._auto_restart = True
        self._extra_power_monitor_group = ""

    @property
    def group_id(self):
        """Return the name of the PowerMonitor."""
        return self._group_id

    @property
    def power_key(self):
        """Return the name of the PowerMonitor."""
        return self._power_key

    @property
    def max_power(self):
        """Return the name of the PowerMonitor."""
        return self._max_power

    @property
    def max_power_conf(self):
        """Return the name of the PowerMonitor."""
        return self._max_power_conf

    @property
    def auto_restart(self):
        """Return the name of the PowerMonitor."""
        return self._auto_restart

    @property
    def extra_power_monitor_group(self):
        """Return the group_id of the extra powe monitor."""
        return self._extra_power_monitor_group

    def set_auto_restart(self, auto_restart):
        self._auto_restart = auto_restart

    def set_extra_power_monitor(self, monitor_group):
        self._extra_power_monitor_group = monitor_group


async def async_setup(hass, config):
    """Set up the asusrouter component."""

    monitors_conf = []

    if DOMAIN in config:
        monitors_conf = config[DOMAIN][CONF_GROUPS]

    power_monitor = dict()
    monitors = []
    for conf in monitors_conf:

        monitor = PowerMonitor(
            conf[CONF_GROUP_ID],
            conf[CONF_POWER_KEY],
            conf[CONF_MAX_POWER],
            conf[CONF_MAX_POWER_CONF]   
        )
        
        monitor.set_auto_restart(conf[CONF_AUTO_RESTART])
        monitor.set_extra_power_monitor(conf[CONF_EXTRA_POWER_MONITOR])
        monitors.append(monitor)

    power_monitor['name'] = config[DOMAIN][CONF_NAME]
    power_monitor['groups'] = monitors
    hass.data[DATA_POWERMON] = power_monitor

    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )


    async def _turn_all_on(call):
        """Restart a router."""

        try:

            id_list = call.data[CONF_ID_LIST]
            if id_list:
                turn_list = id_list.strip('[]').split(',')
                for item in turn_list:
                    item = item.strip(' \'')

                    await hass.services.async_call("switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: item})

        except Exception as e:
            _LOGGER.error(e)

            
    hass.services.async_register(
        DOMAIN, SERVICE_TURN_ALL_ON, _turn_all_on, schema=SERVICE_TURN_ALL_ON_SCHEMA
    )
    

    return True
          
