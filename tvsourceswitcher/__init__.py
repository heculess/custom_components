"""Support for TVSourceSwitcher devices."""
import logging
import voluptuous as vol

from datetime import datetime, timedelta
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
)

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE_ID = 'device_id'
CONF_DEFAULT_CHANNEL = 'default_channel'
CONF_POWER_OVER_CHANNEL = 'power_over_channel'
CONF_MAX_DEFAULT_POWER = 'default_power'
CONF_DEVICE_CHANNEL = 'channel'
CONF_POWER_MON = 'power'

DOMAIN = "tvsourceswitcher"
DATA_SWITCHMON = DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_DEVICE_ID): cv.string,
                vol.Required(CONF_DEFAULT_CHANNEL): cv.string,
                vol.Required(CONF_MAX_DEFAULT_POWER): cv.positive_int,
                vol.Required(CONF_POWER_OVER_CHANNEL): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_SELECT_CHANNEL = "select_channel"
SERVICE_SELECT_CHANNEL_SCHEMA = vol.Schema({vol.Required(CONF_DEVICE_CHANNEL): cv.string})

SERVICE_AUTO_SELECT_CHANNEL = "auto_select_channel"
SERVICE_AUTO_SELECT_CHANNEL_SCHEMA = vol.Schema({vol.Required(CONF_POWER_MON): cv.string})

class TVSourceSwitcher:
    """interface of a power monitor."""

    def __init__(self, conf_name, hass):
        """Init function."""
        self._name = conf_name
        self._hass = hass
        self._device_id = None
        self._default_channel = None
        self._default_power = None
        self._power_over_channel = None
        self._channel_to_change = None
        self._last_change_time = None
        self._last_trigger_time = None

    @property
    def name(self):
        """Return the name of the TVSourceSwitcher."""
        return self._name

    @property
    def device_id(self):
        """Return the TV device id."""
        return self._device_id

    @property
    def default_channel(self):
        """Return the tv default channel"""
        return self._default_channel

    @property
    def default_power(self):
        """Return the default power"""
        return self._default_power

    @property
    def power_over_channel(self):
        """Return the tv channel when power is over"""
        return self._power_over_channel

    def set_device_id(self, device_id):
        self._device_id = device_id

    def set_default_channel(self, channel):
        self._default_channel = channel

    def set_default_power(self, power):
        self._default_power = power

    def set_power_over_channel(self, channel):
        self._power_over_channel = channel

    def update_trigger_time(self):

        if not self._last_trigger_time:
             return 

        if (datetime.now() - self._last_trigger_time).total_seconds() > 30:
            self._last_trigger_time = None
            self._channel_to_change = None

    def is_change_forbidden(self):

        if not self._last_change_time:
            if self._channel_to_change:
                return True
        else:
            if (datetime.now() - self._last_change_time).total_seconds() < 5:
                return True

        return False

    async def change_channel(self, channel, force):

        try:
            item = self._hass.states.get(self._device_id)
            if not item:
                return

            if item.state == 'on' :

                self.update_trigger_time()

                if not force:
                    if self.is_change_forbidden():
                        return

                await self._hass.services.async_call("media_player", "play_media", 
                    {ATTR_ENTITY_ID: self.device_id, "media_content_type": "channel", "media_content_id": channel})
                await self._hass.services.async_call("media_player", "select_source", 
                    {ATTR_ENTITY_ID: self.device_id, "source": channel})
                    
                self._last_change_time = datetime.now()
                self._channel_to_change = None
            else:
                self._channel_to_change = channel
                self._last_trigger_time = datetime.now()

        except Exception as e:
            _LOGGER.error(e)

    async def attach_state_change(self, event):

        try:
            if event.data.get("entity_id") != self._device_id:
                return

            state = event.data.get("new_state")
            if not state:
                return
                
            if state.state != 'on' :
                self._last_change_time = None
                self._last_trigger_time = None
                return
            _LOGGER.debug("----------------------------------------- channel to change : %s" % self._channel_to_change)			
            if self._channel_to_change:
                await self.change_channel(self._channel_to_change,True)
        except Exception as e:
            _LOGGER.error(e)
        

async def async_setup(hass, config):
    """Set up the asusrouter component."""

    conf = []

    if DOMAIN in config:
        conf = config[DOMAIN]

        switcher = TVSourceSwitcher(conf[CONF_NAME],hass)
        switcher.set_device_id(conf[CONF_DEVICE_ID])
        switcher.set_default_channel(conf[CONF_DEFAULT_CHANNEL])
        switcher.set_default_power(conf[CONF_MAX_DEFAULT_POWER])
        switcher.set_power_over_channel(conf[CONF_POWER_OVER_CHANNEL])

        hass.data[DATA_SWITCHMON] = switcher
    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    async def _select_channel(call):
        """select a channel."""
        device = hass.data[DOMAIN]

        try:
            _LOGGER.info("----------------------------------------- services call select_channel")
            await device.change_channel(call.data[CONF_DEVICE_CHANNEL],True)

        except Exception as e:
            _LOGGER.error(e)

            
    hass.services.async_register(
        DOMAIN, SERVICE_SELECT_CHANNEL, _select_channel, schema=SERVICE_SELECT_CHANNEL_SCHEMA
    )


    async def _auto_select_channel(call):
        """auto select a channel by power."""
        device = hass.data[DOMAIN]
        try:

            power = float(call.data[CONF_POWER_MON])
            if power > float(device.default_power):
                await device.change_channel(device.power_over_channel,False)
            else:
                await device.change_channel(device.default_channel,False)

        except Exception as e:
            _LOGGER.error(e)

            
    hass.services.async_register(
        DOMAIN, SERVICE_AUTO_SELECT_CHANNEL, _auto_select_channel, schema=SERVICE_AUTO_SELECT_CHANNEL_SCHEMA
    )


    async def _on_state_change(event):
        """auto select a channel by power."""
        device = hass.data[DOMAIN]
        try:

            await device.attach_state_change(event)

        except Exception as e:
            _LOGGER.error(e)

    hass.bus.async_listen(EVENT_STATE_CHANGED,_on_state_change)
    return True

