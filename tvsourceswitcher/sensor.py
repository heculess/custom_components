"""Asusrouter status sensors."""
import logging
import math
from datetime import datetime
from homeassistant.helpers.entity import Entity
from . import TVSourceSwitcher
from . import DATA_SWITCHMON

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the asusrouter."""

    devices = []
    devices.append(TVSourceSwitcherSensor(hass))
    add_entities(devices, True)


class TVSourceSwitcherSensor(Entity):
    """Representation of a asusrouter."""

    def __init__(self, hass):
        """Initialize the router."""
        self._monitor = hass.data[DATA_SWITCHMON]
        self._name = self._monitor.name
        self._hass = hass

    @property
    def name(self):
        """Return the name of the ddns."""
        return self._name

    @property
    def state(self):
        """Return the state of the ddns."""
        return self._state

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {
        }

    async def async_update(self):
        """Fetch status from router."""

        try:
           
            self._state = "checked"

        except  Exception as e:
            _LOGGER.error(e)
            self._state = "check error"
