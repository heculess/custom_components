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
CONF_MIN_FUR_CHECK = 'min_fur_check'
CONF_FUR_SWITCH_NAME = 'fur_switch_name'

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
                vol.Optional(CONF_FUR_SWITCH_NAME,default=""): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_TURN_ALL_ON = "turn_all_on"
SERVICE_TURN_ALL_ON_SCHEMA = vol.Schema({vol.Required(CONF_ID_LIST): cv.string})


class SwitchMonitor:
    """interface of a power monitor."""

    def __init__(self, group_id, confirm_check, conf_name,min_further_check,further_switch_name):
        """Init function."""
        self._group_id = group_id
        self._confirm_check = confirm_check
        self._min_further_check = min_further_check
        self._further_switch_name = further_switch_name
        self._name = conf_name
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
    def further_switch_name(self):
        """Return the further switch name of switch"""
        return self._further_switch_name


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
                    if not item:
                        continue

                    if device.need_further_operation(item):
                        fur_switch = hass.states.get(item).attributes.get(device.further_switch_name)
                        if(fur_switch):
                            await hass.services.async_call("switch", SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fur_switch})
                        await device.remove_turn_count_dict(item)
                    else:
                        await hass.services.async_call("switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: item})
                        await device.remove_from_state_off_dict(item)

        except Exception as e:
            _LOGGER.error(e)

            
    hass.services.async_register(
        DOMAIN, SERVICE_TURN_ALL_ON, _turn_all_on, schema=SERVICE_TURN_ALL_ON_SCHEMA
    )
    

    return True

