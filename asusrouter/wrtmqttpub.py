"""Module for LedeWrt."""
import logging
import json
from homeassistant.util import dt as dt_util
from .const import *

from homeassistant.const import (
    ATTR_NOW,
    EVENT_TIME_CHANGED,
)

_LOGGER = logging.getLogger(__name__)

class WrtMqttPub:
    def __init__(self, hass, publish):
        self._hass = hass
        self._state_publish = False
        self._network_publish = False
        self._mqtt = hass.components.mqtt
        self._last_pub_time = dt_util.utcnow()
        self._last_pub_states = {}
        self._router_state = {}
        self._network_state = {}

        self._hass.bus.async_listen(EVENT_TIME_CHANGED,self._on_time_change)

        mqtt = hass.components.mqtt
        if mqtt:
            _LOGGER.debug("subscribe mqtt topic")
            
        pub_list = publish.split(',')
        _LOGGER.debug(pub_list)
        for pub in pub_list:
            if pub == "state":
                self._state_publish = True
                _LOGGER.debug("AsusWrtMqtt : publish states")
            if pub == "network":
                self._network_publish = True
                _LOGGER.debug("AsusWrtMqtt : publish network")

    def update_router_state(self, name, states):
        network_states = {}

        try:
            network_states[NETWORK_STATE_DOWNLOAD_SPEED] = states.pop(NETWORK_STATE_DOWNLOAD_SPEED)
            network_states[NETWORK_STATE_UPLOAD_SPEED] = states.pop(NETWORK_STATE_UPLOAD_SPEED)
            network_states[NETWORK_STATE_DOWNLOAD] = states.pop(NETWORK_STATE_DOWNLOAD)
            network_states[NETWORK_STATE_UPLOAD] = states.pop(NETWORK_STATE_UPLOAD)
            
            self._network_state[name] = json.dumps(network_states)
            self._router_state[name] = json.dumps(states)
        except Exception as e:
            self._router_state = {}
            self._network_state = {}
            _LOGGER.error(e)
    
    async def _on_time_change(self, event):
        try:
            time_now = event.data.get(ATTR_NOW)
            if not time_now:
                return

            time_diff = time_now - self._last_pub_time
            if time_diff.total_seconds() < 60 :
                return

            if self._state_publish == True:
                _LOGGER.debug("AsusWrtMqtt : %s" % self._state_publish)
                mqtt_publish = {}
                for key,value in self._router_state.items():

                    update_state = False
                    if key in self._last_pub_states:
                        if value != self._last_pub_states[key] :
                            update_state = True  
                    else :
                        update_state = True

                    if update_state :
                        self._last_pub_states[key] = value
                        mqtt_publish[key] = value

                states =  json.dumps(mqtt_publish)
                _LOGGER.debug("mqtt publish routers states")
                _LOGGER.debug(states)
                    
                self._mqtt.publish(MQTT_STATES_UPDATE_TOPIC,states)

            if self._network_publish == True:
                
                _LOGGER.debug("mqtt publish routers network information")      
                self._mqtt.publish(MQTT_STATES_NETWORK_TOPIC,json.dumps(self._network_state))

            _LOGGER.debug(time_now)
            self._last_pub_time = time_now

        except Exception as e:
            _LOGGER.error(e)

    async def force_update_states(msg):
        """Handle new MQTT messages."""
        param = json.loads(msg.payload)
        update_list = param['list']
        _LOGGER.debug("mqtt force update device")
        if not offline_list:
            return

        for update_item in update_list:
            if update_item in self._last_pub_states:
                del self._last_pub_states[update_item]