"""Asusrouter status sensors."""
import logging
import math
from datetime import datetime
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util
from . import PowerMonitor
from . import DATA_POWERMON

from homeassistant.const import (
    ATTR_NOW,

    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,

    EVENT_STATE_CHANGED,
    EVENT_TIME_CHANGED,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the asusrouter."""

    monitors = hass.data[DATA_POWERMON]['groups']
    name = hass.data[DATA_POWERMON]['name']
    devices = []
    devices.append(PowerMonitorSensor(hass, name, monitors))
    add_entities(devices, True)

class PowerSensor(Entity):
    """Representation of a asusrouter."""

    def __init__(self, hass, monitor):
        """Initialize the router."""
        self._group_id = monitor.group_id
        self._power_key = monitor.power_key
        self._max_power = monitor.max_power
        self._max_power_conf = monitor.max_power_conf
        self._auto_restart = monitor.auto_restart
        self._last_power_off = ""
        self._ready_to_power_on = ""
        self._hass = hass
        self._current_power = 0.0

        self._last_power_on_stamp = None

        self._hass.bus.async_listen(EVENT_STATE_CHANGED,self._on_state_change)
        self._hass.bus.async_listen(EVENT_TIME_CHANGED,self._on_time_change)

        self._devices_power_dict = {}
        self._state_off_dict = {}

    @property
    def device_to_power_on(self):
        """Return the device to turn on power."""
        return self._ready_to_power_on

    def get_device_power(self, device):
        """Fetch device power."""
        try:
          item = self._hass.states.get(device)
          if not item:
            return 0.0

          if item.state == 'off' :
            self._last_power_off = device

          power = item.attributes.get(self._power_key)
          if not power:
              return 0.0

          return float(power)
        except  Exception as e:
            _LOGGER.error(e)
            return 0.0

    def get_max_power(self):
        """get max power."""
        if self._max_power_conf == "":
          return self._max_power
        else:
          item = self._hass.states.get(self._max_power_conf)
          if not item:
            return self._max_power
          return float(item.state)

    def update_current_power(self):

        self._current_power = 0.0

        for device in self._devices_power_dict.keys():
            power = self.get_device_power(device)
            if power > 0.0:
                self._current_power += power

            self._devices_power_dict[device] = power

    def is_ready_to_power_on(self):

        if not self._last_power_on_stamp:
            return True

#        if self.get_max_power() - self._current_power >500 :
#            return True

        time_diff = dt_util.utcnow() - self._last_power_on_stamp
        if time_diff.total_seconds() > 300:
            return True

        return False

    async def power_on_switch(self,switch_to_power_on):
   
        if self.is_ready_to_power_on():
            await self._hass.services.async_call("switch", 
                SERVICE_TURN_ON, {ATTR_ENTITY_ID: switch_to_power_on})
            self._last_power_on_stamp = dt_util.utcnow()

    async def get_power_count(self):
 
        self._last_power_off = ""
        self._ready_to_power_on = ""

        try:
            if not self._devices_power_dict :
                self._devices_power_dict = dict.fromkeys(
                    self._hass.states.get(self._group_id).attributes.get('entity_id'))
                _LOGGER.debug(" Get group devices : %s", str(self._devices_power_dict))

            self.update_current_power()

            if self._current_power < self.get_max_power():
                self._ready_to_power_on = self._last_power_off

                if self._auto_restart and self._ready_to_power_on:
                    _LOGGER.debug(" Turn on the device : %s", self._ready_to_power_on)
                    await self.power_on_switch(self._ready_to_power_on)

            return self._current_power
                    
        except  Exception as e:
            _LOGGER.error(e)
            return 0.0


    async def _on_state_change(self, event):
        try:
            state = event.data.get("new_state")
            if not state:
                return

            triger_id = event.data.get("entity_id")

            if triger_id == self._group_id and state.state == "off":
                self._state_off_dict.clear()
            
            if triger_id not in self._devices_power_dict.keys():
                return

            old_state = event.data.get("old_state")
            if old_state and old_state.state == "on" and state.state == "off":
                _LOGGER.debug("devices %s states change to %s", triger_id, state.state)
                self._state_off_dict[triger_id] = dt_util.utcnow()
                return

            if state.state == "on":

                self.update_current_power()

                if triger_id in self._state_off_dict.keys():
                    del self._state_off_dict[triger_id]

        except Exception as e:
            _LOGGER.error(e)

    async def _on_time_change(self, event):
        try:
            time_now = event.data.get(ATTR_NOW)
            if not time_now:
                return

            for device, stamp in self._state_off_dict.items():
                time_diff = time_now - stamp
                _LOGGER.debug("state since last change to off")
                _LOGGER.debug(time_diff)
                if time_diff.total_seconds() > 10:
                    if self._current_power < self.get_max_power():
                        await self._hass.services.async_call("switch", 
                            SERVICE_TURN_ON, {ATTR_ENTITY_ID: device})
                        self._state_off_dict[device] = time_now
                        return

        except Exception as e:
            _LOGGER.error(e)
       

class PowerMonitorSensor(Entity):
    """Representation of a asusrouter."""

    def __init__(self, hass, name, monitors):
        """Initialize the router."""
        self._name = name
        self._state = None
        self._ready_to_power_on = []
        self._monitor_list = []
        self._hass = hass

        for monitor in monitors:
            self._monitor_list.append(PowerSensor(hass, monitor))   

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
            'ready_to_power_on': self._ready_to_power_on if self._ready_to_power_on else ""
        }

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "w"

    async def async_update(self):
        """Fetch status from router."""
        try:
            self._ready_to_power_on = []

            power_count = 0.0

            for monitor in self._monitor_list:
                power_count += await monitor.get_power_count()

                if monitor.device_to_power_on :
                    self._ready_to_power_on.append(monitor.device_to_power_on)

            self._state = "%.2f" % (power_count)
        
        except  Exception as e:
            _LOGGER.error(e)
            self._state = "0.0"
