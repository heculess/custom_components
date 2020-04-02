"""Asusrouter status sensors."""
import logging
import math
from datetime import datetime
from homeassistant.helpers.entity import Entity
from . import SwitchMonitor
from . import DATA_SWITCHMON

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the asusrouter."""

    devices = []
    devices.append(SwitchMonitorSensor(hass))
    add_entities(devices, True)


class SwitchMonitorSensor(Entity):
    """Representation of a asusrouter."""

    def __init__(self, hass):
        """Initialize the router."""
        self._monitor = hass.data[DATA_SWITCHMON]
        self._name = self._monitor.name
        self._check_confirm = []
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
            'state_off_list': self._check_confirm if self._check_confirm else "",
        }

    def get_turn_off_list(self,id_list):
        """Fetch trun off switch."""
        turn_off_dict = dict()
        try:
            for device in id_list:
                item = self._hass.states.get(device)
                if not item:
                    continue
                if item.state == 'unavailable':
                    continue
                if item.state != 'on' :
                    turn_off_dict[device] = 1
            return turn_off_dict
        except  Exception as e:
            _LOGGER.error(e)
            return dict()

    async def async_update(self):
        """Fetch status from router."""

        try:
            ready_to_turn_on = []

            id_list = self._hass.states.get(self._monitor.group_id).attributes.get('entity_id')
            current_off_dict = self.get_turn_off_list(id_list)
           
            self._check_confirm =  await self._monitor.update_state_off_dict(current_off_dict)

            if self._check_confirm:
                self._state = "checked"
            else:
                self._state = "checking"

        except  Exception as e:
            _LOGGER.error(e)
            self._state = "check error"
