"""Support for SwitchMonitor devices."""
import logging
import voluptuous as vol

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    CONF_NAME,
)

_LOGGER = logging.getLogger(__name__)

CONF_GROUP_ID = 'group_id'
CONF_CONFIRM_CHECK = 'confirm_check'
CONF_ID_LIST = 'id_list'
CONF_ID_DEVICE = 'id'
CONF_MIN_FUR_CHECK = 'min_fur_check'
CONF_FUR_SWITCH_NAME = 'fur_switch_name'
CONF_INTERVALE = 'interval'

DOMAIN = "switchmonitor"
DATA_SWITCHMON = DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_GROUP_ID): cv.string,
                vol.Optional(CONF_CONFIRM_CHECK,default=5): cv.positive_int,
                vol.Optional(CONF_MIN_FUR_CHECK,default=3): cv.positive_int,
                vol.Optional(CONF_INTERVALE,default=300): cv.positive_int,
                vol.Optional(CONF_FUR_SWITCH_NAME,default=""): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_TURN_ALL_ON = "turn_all_on"
SERVICE_TURN_ALL_ON_SCHEMA = vol.Schema({vol.Required(CONF_ID_LIST): cv.string})

SERVICE_TURN_ON_DEVICE = "turn_on_device"
SERVICE_TURN_ON_DEVICE_SCHEMA = vol.Schema({vol.Required(CONF_ID_DEVICE): cv.string})


class SwitchMonitor:
    """interface of a power monitor."""

    def __init__(self, group_id, confirm_check, conf_name,min_further_check,further_switch_name):
        """Init function."""
        self._group_id = group_id
        self._confirm_check = confirm_check
        self._min_further_check = min_further_check
        self._further_switch_name = further_switch_name
        self._name = conf_name
        self._interval = None
        self._state_off_dict = {}
        self._turn_on_count_dict = {}

    @property
    def name(self):
        """Return the name of the SwitchMonitor."""
        return self._name

    @property
    def group_id(self):
        """Return the name of the SwitchMonitor."""
        return self._group_id

    @property
    def confirm_check(self):
        """Return the max times of the confirm"""
        return self._confirm_check

    @property
    def check_interval(self):
        """Return the interval"""
        return self._interval

    @property
    def further_switch_name(self):
        """Return the further switch name of switch"""
        return self._further_switch_name

    def set_auto_check_interval(self, interval):
        self._interval = interval

    def need_further_operation(self, item):
        if not item:
            return False

        if self._further_switch_name == "":
            return False

        if item not in self._turn_on_count_dict:
           return False 
            
        if self._turn_on_count_dict[item] > self._min_further_check:
           return True

        return False

    async def update_turn_on_count_dict(self, new_off_dict):
        if not self._turn_on_count_dict:
            return
        try:
            new_dict = dict()
            for switch in self._turn_on_count_dict:
                if switch in new_off_dict:
                    new_dict[switch] = self._turn_on_count_dict[switch]

            self._turn_on_count_dict = new_dict

        except Exception as e:
            _LOGGER.error(e)

    async def remove_from_state_off_dict(self, item):
        if not item:
            return
        try:
            if item in self._state_off_dict:
                self._state_off_dict.pop(item)

            if item in self._turn_on_count_dict:
                self._turn_on_count_dict[item] += 1
            else:
                self._turn_on_count_dict[item] = 1

        except Exception as e:
            _LOGGER.error(e)

    async def remove_turn_count_dict(self, item):
        if not item:
            return

        try:
          
            if item in self._turn_on_count_dict:
                self._turn_on_count_dict.pop(item)

        except Exception as e:
            _LOGGER.error(e)

    async def update_state_off_dict(self, current_off_dict):
        ready_to_turn_on = []
        await self.update_turn_on_count_dict(current_off_dict)
        try:
            new_off_dict = dict()

            if self._state_off_dict:
                for switch in self._state_off_dict:
                    if switch in current_off_dict:
                        new_off_dict[switch] = self._state_off_dict[switch] + 1
                        current_off_dict.pop(switch)

                        if new_off_dict[switch] > self._confirm_check:
                            ready_to_turn_on.append(switch)

            self._state_off_dict = new_off_dict

            if current_off_dict:
                self._state_off_dict.update(current_off_dict)

            return ready_to_turn_on

        except Exception as e:
            _LOGGER.error(e)
            return []

    def get_device_by_id(self, id, hass_states):
        if not id:
            return None
        try:

            id_list = hass_states.get(self._group_id).attributes.get('entity_id')
            for device in id_list:
                dev_id = device.split('_')
                if dev_id[1] == id:
                    return device

            return None
            
        except Exception as e:
            _LOGGER.error(e)

    async def resume_device(self, item, hass, operator):
        """resume the device network."""
        if not item:
            return

        if self.need_further_operation(item):
            fur_switch = hass.states.get(item).attributes.get(self.further_switch_name)
            if(fur_switch):
                _LOGGER.warning("%s turn off device %s" % (operator, fur_switch))
                await hass.services.async_call("switch", SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fur_switch})
            else:
                _LOGGER.warning("miss device further infomation %s" % (fur_switch))
            await self.remove_turn_count_dict(item)
        else:
            _LOGGER.warning("%s turn on device %s" % (operator, item))
            await hass.services.async_call("switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: item})
            await self.remove_from_state_off_dict(item)

async def async_setup(hass, config):
    """Set up the asusrouter component."""

    conf = []

    if DOMAIN in config:
        conf = config[DOMAIN]

        hass.data[DATA_SWITCHMON] = SwitchMonitor(
            conf[CONF_GROUP_ID],
            conf[CONF_CONFIRM_CHECK],
            conf[CONF_NAME],
            conf[CONF_MIN_FUR_CHECK],
            conf[CONF_FUR_SWITCH_NAME],
        )

        hass.data[DATA_SWITCHMON].set_auto_check_interval(conf[CONF_INTERVALE])

    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    async def _turn_all_on(call):
        """Restart a router."""
        device = hass.data[DOMAIN]

        try:

            id_list = call.data[CONF_ID_LIST]
            if id_list:
                turn_list = id_list.strip('[]').split(',')
                for item in turn_list:
                    item = item.strip(' \'')
                    _LOGGER.debug("SwitchMonitorSensor-----------turn on devices: %s", item)
                    await device.resume_device(item, hass,"SwitchMonitor")

        except Exception as e:
            _LOGGER.error(e)

            
    hass.services.async_register(
        DOMAIN, SERVICE_TURN_ALL_ON, _turn_all_on, schema=SERVICE_TURN_ALL_ON_SCHEMA
    )
    

    async def _turn_on_device(call):
        """Restart a router."""
        device = hass.data[DOMAIN]

        try:

            id = call.data[CONF_ID_DEVICE]
            if not id:
                return

            await device.resume_device(device.get_device_by_id(id, hass.states), hass,"mqtt")

        except Exception as e:
            _LOGGER.error(e)

            
    hass.services.async_register(
        DOMAIN, SERVICE_TURN_ON_DEVICE, _turn_on_device, schema=SERVICE_TURN_ON_DEVICE_SCHEMA
    )

    return True

