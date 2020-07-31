"""Support for TIMERSWITCH devices."""
import logging
import json
import voluptuous as vol
import pytz
import enum

from homeassistant.const import (
    ATTR_NOW,
    ATTR_ENTITY_ID,

    CONF_NAME,
    CONF_BEFORE,
    CONF_AFTER,
    CONF_CONDITION,
    CONF_ENTITY_ID,

    EVENT_STATE_CHANGED,
    EVENT_TIME_CHANGED,

    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util
from datetime import datetime, timedelta, timezone

_LOGGER = logging.getLogger(__name__)


DOMAIN = "timer_switch"

CONF_SWITCHS = "switchs"
CONF_SWITCH_TARGET = "target"

CONF_TIMES = "times"

SECRET_GROUP = "Password or SSH Key"
FORMAT_PATTERN = "%H:%M:%S"

TIME_CONFIG = vol.Schema(
    {
        vol.Required(CONF_BEFORE): cv.time,
        vol.Required(CONF_AFTER): cv.time
    },
    extra=vol.ALLOW_EXTRA,
)


SWITCH_CONFIG = vol.Schema(
    {
        vol.Required(CONF_SWITCH_TARGET): cv.string,
        vol.Required(CONF_TIMES, default={}): vol.All(
            cv.ensure_list,
            vol.All([TIME_CONFIG]),
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_SWITCHS, default={}): vol.All(
                    cv.ensure_list,
                    vol.All([SWITCH_CONFIG]),
                ),
                vol.Optional(CONF_CONDITION, default=""): cv.string,
                vol.Optional(CONF_ENTITY_ID, default=""): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

class SpanPosition(enum.Enum):
    SPAN_START = 1
    SPAN_END = 2
    SPAN_IN = 3
    SPAN_OUT = 4

class time_span:

    def __init__(self, after, before):
        """Init function."""
        self._after = after
        self._before = before

        self._after_string = self._after.strftime(FORMAT_PATTERN)
        self._before_string = self._before.strftime(FORMAT_PATTERN)

    def test_span_start_end(self,time):

        time_test = time.strftime(FORMAT_PATTERN)

        if time_test == self._after_string:
            return SpanPosition.SPAN_START
        
        if time_test == self._before_string:
            return SpanPosition.SPAN_END

        return SpanPosition.SPAN_OUT

    def test_in_span(self,time):

        if self._before > self._after :
        
            if time < self._after :
                return SpanPosition.SPAN_OUT

            if time > self._before :
                return SpanPosition.SPAN_OUT

        else :
            after_yesterday = timedelta(self._after.second,
                self._after.minute,self._after.hour) + timedelta(days=-1)
            if timedelta(time.second,time.minute,time.hour) < after_yesterday :
                return SpanPosition.SPAN_OUT

            if time > self._before :
                return SpanPosition.SPAN_OUT

        return SpanPosition.SPAN_IN

class TimerSwitch():
    """interface of a asusrouter."""

    def __init__(self, hass, entity_id):
        """Init function."""
        self._entity_id = entity_id
        self._hass = hass
        self._condition_id = None
        self._condition_state = None

        self._timespan_list = []

        self._inner_switch = False
        self._condition_enable = True

    
    @property
    def condition_id(self):
        """Return id of condition component."""
        return self._condition_id

    def current_in_time_span(self):
        current_time = datetime.utcnow().time()
        for span in self._timespan_list:
            pos = span.test_in_span(current_time)
            if pos == SpanPosition.SPAN_IN :
                return True

        return False  

    def set_condition_state(self, entity_id, state):
        self._condition_id = entity_id
        self._condition_state = state

    def naive_time_to_utc_datetime(self, naive_time):

        current_local_date = dt_util.utcnow().astimezone(
            self._hass.config.time_zone
        ).date()
        utc_datetime = self._hass.config.time_zone.localize(
            datetime.combine(current_local_date, naive_time)
        ).astimezone(tz=pytz.UTC)
        return utc_datetime

    def add_timer(self, before, after):
        
        span = time_span(self.naive_time_to_utc_datetime(after).time(),
            self.naive_time_to_utc_datetime(before).time())
        self._timespan_list.append(span)

    async def initialization(self):
        if self.current_in_time_span():
            await self.turn_on_switch(True)
        else :
            await self.turn_on_switch(False)

    async def set_switch(self, turn_on):

        item = self._hass.states.get(self._entity_id)
        if not item:
            _LOGGER.error("can not find switch %s" % self._entity_id)
            return

        if item.state == 'unavailable' :
            _LOGGER.error("switch %s is unavailable" % self._entity_id)
            return

        if turn_on :
            await self._hass.services.async_call("switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: self._entity_id})
        else :
            await self._hass.services.async_call("switch", SERVICE_TURN_OFF, {ATTR_ENTITY_ID: self._entity_id})

    async def turn_on_switch(self, turn_on):
        if turn_on :
            self._inner_switch = True
        else :
            self._inner_switch = False

        if not self._inner_switch :
            await self.set_switch(False)
        else :
            if self._condition_enable :
                await self.set_switch(True)
                
        _LOGGER.debug("-----------------turn_on_switch :---------------------------")
        _LOGGER.debug(self._inner_switch)

    async def attach_state_change(self, event):

        try:

            if event.data.get("new_state").state != self._condition_state :
                self._condition_enable = False
            else :
                self._condition_enable = True

            _LOGGER.debug("-----------------%s  state change to : %s" % (self._condition_id,
                event.data.get("new_state").state))	

            if not self._condition_enable:
                await self.set_switch(False)
            else:
                if self._inner_switch:
                    await self.set_switch(True)

        except Exception as e:
            _LOGGER.error(e)

    async def attach_time_change(self, time):

        for span in self._timespan_list:
            pos = span.test_span_start_end(time.time())
            if pos == SpanPosition.SPAN_START:
                await self.turn_on_switch(True)
            if pos == SpanPosition.SPAN_END:
                await self.turn_on_switch(False)

async def async_setup(hass, config):
    """Set up the asusrouter component."""

    timer_switch_config = []

    if DOMAIN in config:
        timer_switch_config = config[DOMAIN][CONF_SWITCHS]

    switchs = []

    for switch_config in timer_switch_config:
        switch = TimerSwitch(hass, switch_config[CONF_SWITCH_TARGET])
        timers_config = switch_config[CONF_TIMES]
        for timer in timers_config:
            switch.add_timer(timer[CONF_BEFORE],timer[CONF_AFTER])

        switch.set_condition_state(config[DOMAIN][CONF_ENTITY_ID],
            config[DOMAIN][CONF_CONDITION])

        await switch.initialization()
        switchs.append(switch)

    hass.data[DOMAIN] = switchs
    

    async def _on_state_change(event):
        devices = hass.data[DOMAIN]
        try:
            state = event.data.get("new_state")
            if not state:
                return

            for device in devices:

                if event.data.get("entity_id") != device.condition_id:
                    return
                await device.attach_state_change(event)

        except Exception as e:
            _LOGGER.error(e)

    async def _on_time_change(event):
        devices = hass.data[DOMAIN]
        try:
            time_now = event.data.get(ATTR_NOW)
            if not time_now:
                return

            for device in devices:
                await device.attach_time_change(time_now)

        except Exception as e:
            _LOGGER.error(e)

    hass.bus.async_listen(EVENT_STATE_CHANGED,_on_state_change)
    hass.bus.async_listen(EVENT_TIME_CHANGED,_on_time_change)
    return True
          
