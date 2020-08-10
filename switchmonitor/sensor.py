"""Asusrouter status sensors."""
import logging
import math
from datetime import datetime
from homeassistant.helpers.entity import Entity
from . import SwitchMonitor
from . import DATA_SWITCHMON

from homeassistant.const import (
    ATTR_NOW,

    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,

    EVENT_TIME_CHANGED,
)

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

        self._last_trigger_stamp = None

        if self._monitor.check_interval > 0 :
            self._hass.bus.async_listen(EVENT_TIME_CHANGED,self._on_time_change)

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

    async def auto_resume_state(self):

        if not self._check_confirm :
            return
        
        await self._hass.services.async_call(DATA_SWITCHMON, 
                        "turn_all_on", {"id_list": str(self._check_confirm)})

    async def _on_time_change(self, event):
        try:

            time_now = event.data.get(ATTR_NOW)
            if not time_now:
                return

            if not self._last_trigger_stamp :
                self._last_trigger_stamp = time_now
                return
               
            time_diff = time_now - self._last_trigger_stamp
            if time_diff.total_seconds() < self._monitor.check_interval:
                return

            self._last_trigger_stamp = time_now
            _LOGGER.debug("SwitchMonitorSensor-----------auto_check_state : %s", time_now.strftime("%H:%M:%S"))

            await self.auto_resume_state()

        except Exception as e:
            _LOGGER.error(e)