"""Asusrouter status sensors."""
import logging
import math
from datetime import datetime
from homeassistant.helpers.entity import Entity
from . import PowerMonitor
from . import DATA_POWERMON

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the asusrouter."""

    power_monitor = hass.data[DATA_POWERMON]

    devices = []
    devices.append(PowerMonitorSensor(hass, power_monitor))
    add_entities(devices, True)


class PowerMonitorSensor(Entity):
    """Representation of a asusrouter."""

    def __init__(self, hass, monitor_conf):
        """Initialize the router."""
        self._name = monitor_conf.name
        self._state = None
        self._group_id = monitor_conf.group_id
        self._power_key = monitor_conf.power_key
        self._max_power = monitor_conf.max_power
        self._max_power_conf = monitor_conf.max_power_conf
        self._last_power_off = ""
        self._ready_to_power_on = ""
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
            'ready_to_power_on': self._ready_to_power_on,
        }

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "w"

    def get_device_power(self,device):
        """Fetch device power."""
        try:
          item = self._hass.states.get(device)
          if not item:
            return 0.0
          if item.state != 'on' :
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

    async def async_update(self):
        """Fetch status from router."""
        power_count = 0.0
        self._last_power_off = ""
        self._ready_to_power_on = ""

        try:
            max_power = self.get_max_power()
            id_list = self._hass.states.get(self._group_id).attributes.get('entity_id')
            for device in id_list:
                power = self.get_device_power(device)
                if power > 0.0:
                    power_count += power
            self._state = "%.2f" % (power_count)
            if power_count < max_power:
                self._ready_to_power_on = self._last_power_off
        except  Exception as e:
            _LOGGER.error(e)
            self._state = "0.0"
