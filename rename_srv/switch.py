
import logging
import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
import homeassistant.helpers.config_validation as cv

from . import DOMAIN_SRV
#from .http import RenameGateway

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):

    switches = []
    switches.append(RenameSrvSwitche(hass.data[DOMAIN_SRV], hass))
    add_entities(switches)


class RenameSrvSwitche(SwitchEntity):

    def __init__(self, server, hass):
        """Initialize the switch."""
        self._server = server
        self._hass = hass

    def turn_on(self, **kwargs):
        """Turn on the device."""
        self._server.srv_start()

    def turn_off(self, **kwargs):
        """Turn off the device."""
        self._server.srv_stop()

    @property
    def name(self):
        """Return the name of the switch."""
        _LOGGER.info("[renamesrv_gateway] RenameSrvSwitche name:%s\n" % self._server.srv_name())
        return self._server.srv_name()

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._server.is_running()

    @property
    def icon(self):
        """Return the robot icon to match Home Assistant automations."""
        return "mdi:server"