"""Asusrouter status sensors."""
import logging
from homeassistant.helpers.entity import Entity
from . import DevicesCounter
from . import DATA_DEVICESCOUNTER

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):

    devices = []
    devices.append(DevicesCounterSensor(hass))
    add_entities(devices, True)


class DevicesCounterSensor(Entity):
    def __init__(self, hass):
        """Initialize the router."""
        self._counter = hass.data[DATA_DEVICESCOUNTER]
        self._name = self._counter.name
        self._hass = hass

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    def get_devices_count(self,id_list):
        count_total = 0
        try:
            for device in id_list:
                item = self._hass.states.get(device)
                if not item:
                    _LOGGER.warning("can not find device" + device)
                    continue
                count = item.attributes.get('client_number')
                if not count:
                    continue
                count_total += int(count)
            return count_total
        except  Exception as e:
            _LOGGER.error(e)
            return dict()

    async def async_update(self):

        try:
            id_list = self._hass.states.get(self._counter.group_id).attributes.get('entity_id')
            self._state = "%s" % self.get_devices_count(id_list)

        except  Exception as e:
            _LOGGER.error(e)
            self._state = "not count"
