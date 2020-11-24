"""The lede component."""
import logging
import json
import voluptuous as vol
from .ledewrt import LedeWrt

from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_PORT,
)

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from .const import *
from .wrtmqttpub import WrtMqttPub

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ledewrt"
DATA_LEDEWRT = DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_SSH_PORT): cv.port,
                vol.Exclusive(CONF_PASSWORD, SECRET_GROUP): cv.string,
                vol.Exclusive(CONF_SSH_KEY, SECRET_GROUP): cv.isfile,
                vol.Exclusive(CONF_PUB_KEY, SECRET_GROUP): cv.isfile,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

ROUTER_CONFIG = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_SSH_PORT): cv.port,
        vol.Exclusive(CONF_PASSWORD, SECRET_GROUP): cv.string,
        vol.Exclusive(CONF_SSH_KEY, SECRET_GROUP): cv.isfile,
        vol.Exclusive(CONF_PUB_KEY, SECRET_GROUP): cv.isfile,
        vol.Optional(CONF_USE_TELNET, default=False): cv.boolean,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_ROUTERS, default={}): vol.All(
                    cv.ensure_list,
                    vol.All([ROUTER_CONFIG]),
                ),
                vol.Optional(CONF_ADD_ATTR, default=False): cv.boolean,
                vol.Optional(CONF_PUB_MQTT, default=""): cv.string,
                vol.Optional(CONF_SR_HOST_ID, default=""): cv.string,
                vol.Optional(CONF_SR_CACHING_PROXY, default=""): cv.string,
                vol.Optional(CONF_SR_HOST_PROXY, default=""): cv.string,
                vol.Optional(CONF_MAX_OFFINE_SETTING, default=""): cv.string,
                vol.Optional(CONF_INIT_DNS, default=""): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


SERVICE_REBOOT_SCHEMA = vol.Schema({vol.Required(CONF_HOST): cv.string})

SERVICE_RUN_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_COMMAND_LINE): cv.string,
        vol.Required(CONF_HOST): cv.string,
    }
)

SERVICE_INIT_DEVICE_SCHEMA = SERVICE_RUN_COMMAND_SCHEMA

SERVICE_SET_PORTFORWARD_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SSID): cv.string,
        vol.Optional(CONF_PORT_EXTER, default=5555): cv.port,
        vol.Optional(CONF_PORT_INNER, default=5555): cv.port,
        vol.Optional(CONF_PROTOCOL, default="TCP"): cv.string,
        vol.Required(CONF_TARGETHOST): cv.string,
    }
)

SERVICE_SET_VPN_CONNECT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SSID): cv.string,
        vol.Required(CONF_VPN_SERVER): cv.string,
        vol.Required(CONF_VPN_USERNAME): cv.string,
        vol.Required(CONF_VPN_PASSWORD): cv.string,
        vol.Required(CONF_VPN_PROTOCOL): cv.string,
    }
)


SERVICE_ENABLE_WIFI_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_ENABLE_WIFI): cv.boolean,
        vol.Required(CONF_TYPE_WIFI, default=CONF_NAME_5GWIFI): vol.In(
            [CONF_NAME_2GWIFI, CONF_NAME_5GWIFI]),
    }
)

SERVICE_MAP_CLIENTS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT_BASE, default=5000): cv.port,
        vol.Optional(CONF_PORT_INNER, default=5555): cv.port,
        vol.Optional(CONF_PROTOCOL, default="TCP"): cv.string,
    }
)

async def async_setup(hass, config):
    """Set up the ledewrt component."""

    conf = config[DOMAIN]

    if DOMAIN in config:
        routers_conf = config[DOMAIN][CONF_ROUTERS]

    routers = []
    for conf in routers_conf:
        router = LedeWrt(
            conf[CONF_HOST],
            conf[CONF_NAME],
            conf[CONF_PORT],
            conf[CONF_USERNAME],
            conf.get(CONF_PASSWORD, ""),
            conf.get(CONF_SSH_KEY, conf.get("pub_key", ""))
        )
        await router.set_hass(hass)
        await router.set_add_attribute(config[DOMAIN][CONF_ADD_ATTR])
        await router.set_sr_host_id(config[DOMAIN][CONF_SR_HOST_ID])
        await router.set_caching_proxy(config[DOMAIN][CONF_SR_CACHING_PROXY])
        await router.set_sr_host_proxy(config[DOMAIN][CONF_SR_HOST_PROXY])
        await router.set_max_offline_setting(config[DOMAIN][CONF_MAX_OFFINE_SETTING])
        await router.set_init_dns_line(config[DOMAIN][CONF_INIT_DNS])

        routers.append(router)

    hass.data[DATA_LEDEWRT] = routers
    hass.data[DOMAIN_MQTT_PUB] = WrtMqttPub(hass,config[DOMAIN][CONF_PUB_MQTT])

    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

#    hass.async_create_task(
#        async_load_platform(hass, "device_tracker", DOMAIN, {}, config)
#    )

    async def _reboot(call):
        """Restart a router."""
        devices = hass.data[DOMAIN]
        for device in devices:
            if device.host == call.data[CONF_HOST]:
                await device.reboot()
            
    hass.services.async_register(
        DOMAIN, SERVICE_REBOOT, _reboot, schema=SERVICE_REBOOT_SCHEMA
    )

    async def _run_command(call):
        """Restart a router."""
        devices = hass.data[DOMAIN]
        for device in devices:
            if device.host == call.data[CONF_HOST] or call.data[CONF_HOST] == "ALL":
                await device.run_command(call.data[CONF_COMMAND_LINE])

    hass.services.async_register(
        DOMAIN, SERVICE_RUNCOMMAND, _run_command, schema=SERVICE_RUN_COMMAND_SCHEMA
    )

    async def _init_device(call):
        """Restart a router."""
        devices = hass.data[DOMAIN]
        for device in devices:
            if device.host == call.data[CONF_HOST] or call.data[CONF_HOST] == "ALL":
                await device.init_device(call.data[CONF_COMMAND_LINE])

    hass.services.async_register(
        DOMAIN, SERVICE_INITDEVICE, _init_device, schema=SERVICE_INIT_DEVICE_SCHEMA
    )

    async def _set_port_forward(call):
        """Restart a router."""
        devices = hass.data[DOMAIN]
        for device in devices:
            if device.ssid == call.data[CONF_SSID]:
                await device.set_port_forward(
                    call.data[CONF_PORT_EXTER],
                    call.data[CONF_PORT_INNER],
                    call.data[CONF_PROTOCOL],
                    call.data[CONF_TARGETHOST]
                )

    hass.services.async_register(
        DOMAIN, SERVICE_SET_PORT_FORWARD, _set_port_forward, schema=SERVICE_SET_PORTFORWARD_SCHEMA
    )

    async def _set_vpn_connect(call):
        """Restart a router."""
        devices = hass.data[DOMAIN]
        for device in devices:
            if device.ssid == call.data[CONF_SSID]:
                await device.set_vpn_connect(
                    call.data[CONF_VPN_SERVER],
                    call.data[CONF_VPN_USERNAME],
                    call.data[CONF_VPN_PASSWORD],
                    call.data[CONF_VPN_PROTOCOL]
                )

    hass.services.async_register(
        DOMAIN, SERVICE_SET_VPN_CONNECT, _set_vpn_connect, schema=SERVICE_SET_VPN_CONNECT_SCHEMA
    )

    async def _enable_wifi(call):
        """enable a router wifi."""
        devices = hass.data[DOMAIN]
        for device in devices:
            if device.host == call.data[CONF_HOST] or call.data[CONF_HOST] == "ALL":
                await device.enable_wifi(call.data[CONF_TYPE_WIFI],call.data[CONF_ENABLE_WIFI])

    hass.services.async_register(
        DOMAIN, SERVICE_ENABLE_WIFI, _enable_wifi, schema=SERVICE_ENABLE_WIFI_SCHEMA
    )

    async def _map_client(call):
        """map all clients in a router."""
        devices = hass.data[DOMAIN]
        for device in devices:
            if device.host == call.data[CONF_HOST] or call.data[CONF_HOST] == "ALL":
                await device.map_clients(call.data[CONF_PORT_BASE],
                call.data[CONF_PORT_INNER], call.data[CONF_PROTOCOL])

    hass.services.async_register(
        DOMAIN, SERVICE_MAP_CLIENT, _map_client, schema=SERVICE_MAP_CLIENTS_SCHEMA
    )

    async def _get_adbconn_target(msg):
        """Handle new MQTT messages."""
        param = json.loads(msg.payload)
        devices = hass.data[DOMAIN]
        _LOGGER.debug("mqtt get adb connect information")
        _LOGGER.debug(param)
        for device in devices:
            if device.ssid == param['ssid']:
                try:

                    await device.disable_auto_dns()
                    await device.set_port_forward(
                        5555,5555,'TCP',param['target']
                    )
                    num_list = device.host.split('.')
                    mqtt = hass.components.mqtt
                    msg = "{\"host\": \"%s\", \"domain\": \"%s\", \"public_ip\": \"%s\", \"port\": %s, \"wan2_in_use\": %s}" % (device.host, 
                        hass.states.get(device.sr_host_id).attributes.get('domain'), 
                        hass.states.get(device.sr_host_id).attributes.get('record'), 5000+int(num_list[3]), await device.get_wan2_state())
                    req_id = param.get('requestid')
                    if req_id:
                        mqtt.publish("%s/%s" % (CMD_MQTT_TOPIC,req_id), msg)
                    else:
                        mqtt.publish(CMD_MQTT_TOPIC, msg)

                except  Exception as e:
                    _LOGGER.error(e)

    async def _get_vpn_account(msg):
        """Handle new MQTT messages."""
        param = json.loads(msg.payload)
        devices = hass.data[DOMAIN]
        _LOGGER.debug("mqtt get vpn settings")
        _LOGGER.debug(param)
        for device in devices:
            if device.vpn_user == param['vpn_user']:
                try:
                    mqtt = hass.components.mqtt
                    msg = "{\"user\": \"%s\",\"state\": \"%s\", \"deviceid\": \"%s\", \"server\": \"%s\", \"connect_state\": \"%s\"}" % (device.vpn_user, 
                        "inuse" if device.vpn_enabled else "nouse",device.device_name,device.vpn_server,device.device_state)
                    req_id = param.get('requestid')
                    if req_id:
                        mqtt.publish("%s/%s" % (MQTT_VPN_ACCOUNT_TOPIC,req_id), msg)
                    else:
                        mqtt.publish(MQTT_VPN_ACCOUNT_TOPIC, msg)

                except  Exception as e:
                    _LOGGER.error(e)

    async def _device_offline(msg):
        """Handle new MQTT messages."""
        param = json.loads(msg.payload)
        devices = hass.data[DOMAIN]
        offline_list = param['offline_list']
        _LOGGER.debug("mqtt try to resume devices")
        _LOGGER.debug(param)
        if not offline_list:
            return

        for offline_item in offline_list:
            try:

                for device in devices:

                    if offline_item['online'] > device.get_max_offine(hass):
                        continue

                    if not device.match_device_id(offline_item['id']):
                        continue

                    if not device.wifi_enabled:
                        _LOGGER.warning("router %s is not enabled" % (device.device_name))
                        continue

                    if device.public_ip == "":
                        continue
                    if device.public_ip == "0.0.0.0":
                        continue
                    
                    await hass.services.async_call("switchmonitor", "turn_on_device", {"id": device.device_sn})

            except  Exception as e:
                _LOGGER.error(e)


    async def _change_vpn_user(msg):
        """Handle new MQTT messages."""
        param = json.loads(msg.payload)
        devices = hass.data[DOMAIN]
        _LOGGER.debug("mqtt change vpn connect setting")
        _LOGGER.debug(param)
        try:
            for device in devices:

                if not device.match_device_id(param['id']):
                        continue

                if await device.get_wan2_state() == 1:
                    _LOGGER.warning("mqtt change router's (%s)  vpn server error. can not change with more wans" % device.device_name)
                    continue

                _LOGGER.warning("mqtt change router's (%s)  vpn server to %s" % (device.device_name,
                    param['server']))

                await device.set_vpn_connect(
                        param['server'],param['username'],
                        param['password'],param['protocol']
                    )

        except  Exception as e:
            _LOGGER.error(e)

    async def _update_states(msg):
        """Handle new MQTT messages."""
        devices_pub = hass.data[DOMAIN_MQTT_PUB]
        if not devices_pub:
            return
        await devices_pub.force_update_states(msg)

    async def _mqtt_map_client(msg):
        param = json.loads(msg.payload)
        devices = hass.data[DOMAIN]
        _LOGGER.debug("mqtt map all client on device")
        _LOGGER.debug(param)

        device_id = param.get('id')
        if not device_id:
            _LOGGER.error("lost device id param")
            return

        base_port = param.get('base_port')
        if not base_port:
            base_port = 5000

        inner_port = param.get('internal_port')
        if not inner_port:
            inner_port = 5555

        if base_port > 65535 or inner_port > 65000:
            _LOGGER.error("port number larger than 65000")
            return

        if base_port < 1000:
            _LOGGER.error("base port smaller than 1000")
            return

        protocol = param.get('protocol')
        if not protocol:
            protocol = "TCP"

        try:
            for device in devices:

                if not device.match_device_id(param['id']):
                        continue
                
                map_list = await device.map_clients(base_port,
                    inner_port, protocol)

                mqtt = hass.components.mqtt
                msg = json.dumps(map_list)
                req_id = param.get('requestid')

                _LOGGER.error(msg)

                if req_id:
                    mqtt.publish("%s/%s" % (MQTT_STATES_MAP_CLIENT_TOPIC,req_id), msg)
                else:
                    mqtt.publish(MQTT_STATES_MAP_CLIENT_TOPIC, msg)


        except  Exception as e:
            _LOGGER.error(e)

    mqtt = hass.components.mqtt
    if mqtt:
        _LOGGER.debug("subscribe mqtt topic")
        await mqtt.async_subscribe("router_monitor/global/commad/get_adbconn_target", _get_adbconn_target)
        await mqtt.async_subscribe("router_monitor/global/commad/get_vpn_account", _get_vpn_account)
        await mqtt.async_subscribe(MQTT_DEVICE_OFFLINE_TOPIC, _device_offline)
        await mqtt.async_subscribe(MQTT_CHANGE_VPNUSER_TOPIC, _change_vpn_user)
        await mqtt.async_subscribe(MQTT_CMD_UPDATE_STATES_TOPIC, _update_states)
        await mqtt.async_subscribe(MQTT_MAP_CLIENT_TOPIC, _mqtt_map_client)

    return True
