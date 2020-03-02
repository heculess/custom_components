"""Support for ASUSROUTER devices."""
import logging
import json
import voluptuous as vol

from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_PORT,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from aioasuswrt.asuswrt import AsusWrt

_LOGGER = logging.getLogger(__name__)

CONF_PUB_KEY = "pub_key"
CONF_SENSORS = "sensors"
CONF_SSH_KEY = "ssh_key"
CONF_ADD_ATTR = "add_attribute"
CONF_PUB_MQTT = "pub_mqtt"
CONF_SR_HOST_ID = "sr_host_id"
CONF_SSID = "ssid"
CONF_TARGETHOST = "target_host"
CONF_PORT_EXTER = "external_port"
CONF_PORT_INNER = "internal_port"
CONF_PROTOCOL = "protocol"

CONF_VPN_SERVER = "vpn_server"
CONF_VPN_USERNAME = "vpn_username"
CONF_VPN_PASSWORD = "vpn_password"
CONF_VPN_PROTOCOL = "vpn_protocol"

CONF_COMMAND_LINE = "command_line"

CONF_ENABLE_WIFI = "enable"
CONF_TYPE_WIFI = "wifi_type"

CONF_NAME_2GWIFI = '2.4g'
CONF_NAME_5GWIFI = '5g'

DEFAULT_RETRY = 3

DOMAIN = "asusrouter"
CONF_ROUTERS = "routers"
DATA_ASUSWRT = DOMAIN
DEFAULT_SSH_PORT = 22

CMD_MQTT_TOPIC = "router_monitor/global/commad/on_get_adbconn_target"
MQTT_VPN_ACCOUNT_TOPIC = "router_monitor/global/commad/on_get_vpn_account"
MQTT_DEVICE_OFFLINE_TOPIC = "router_monitor/global/commad/device_offline"
MQTT_CHANGE_VPNUSER_TOPIC = "router_monitor/global/commad/change_vpn_account"

SERVICE_REBOOT = "reboot"
SERVICE_RUNCOMMAND = "run_command"
SERVICE_INITDEVICE = "init_device"
SERVICE_SET_PORT_FORWARD = "set_port_forward"
SERVICE_SET_VPN_CONNECT = "set_vpn_connect"
SERVICE_ENABLE_WIFI = "enable_wifi"
_SET_INITED_FLAG_CMD = "touch /etc/inited ; service restart_firewall"

SECRET_GROUP = "Password or SSH Key"

ROUTER_CONFIG = vol.Schema(
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

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_ROUTERS, default={}): vol.All(
                    cv.ensure_list,
                    vol.All([ROUTER_CONFIG]),
                ),
                vol.Optional(CONF_ADD_ATTR, default=False): cv.boolean,
                vol.Optional(CONF_PUB_MQTT, default=False): cv.boolean,
                vol.Optional(CONF_SR_HOST_ID, default=""): cv.string,
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

class AsusRouter(AsusWrt):
    """interface of a asusrouter."""

    def __init__(self, host, port, devicename, username, password, ssh_key):
        """Init function."""
        super().__init__(host, port, False, username, password, ssh_key)
        self._device_name = devicename
        self._host = host
        self._connect_failed = False
        self._add_attribute = False
        self._pub_mqtt = False
        self._sr_host_id = None
        self._vpn_enabled = False
        self._vpn_user = False
        self._vpn_server = False
        self._public_ip = "0.0.0.0"
        self._ssid = ""

    @property
    def device_name(self):
        """Return the device name of the router."""
        return self._device_name

    @property
    def host(self):
        """Return the host ip of the router."""
        return self._host

    @property
    def connect_failed(self):
        """Return the host ip of the router."""
        return self._connect_failed

    @property
    def pub_mqtt(self):
        """Return the host ip of the router."""
        return  self._pub_mqtt

    @property
    def public_ip(self):
        """Return the host ip of the router."""
        return  self._public_ip

    @property
    def add_attribute(self):
        """Return the host ip of the router."""
        return self._add_attribute

    @property
    def sr_host_id(self):
        """Return the host ip of the router."""
        return  self._sr_host_id

    @property
    def vpn_enabled(self):
        """Return the host ip of the router."""
        return self._vpn_enabled

    @property
    def vpn_user(self):
        """Return the host ip of the router."""
        return self._vpn_user

    @property
    def vpn_server(self):
        """Return the host ip of the router."""
        return self._vpn_server

    @property
    def ssid(self):
        """Return the host ip of the router."""
        return self._ssid

    async def set_ssid(self, ssid):
        self._ssid = ssid

    async def set_add_attribute(self, add_attribute):
        self._add_attribute = add_attribute

    async def set_pub_mqtt(self, pub_mqtt):
        self._pub_mqtt = pub_mqtt

    async def set_sr_host_id(self, sr_host_id):
        self._sr_host_id = sr_host_id

    async def set_vpn_enabled(self, vpn_enable):
        self._vpn_enabled = vpn_enable

    async def set_public_ip(self, public_ip):
        self._public_ip = public_ip

    async def set_vpn_user(self, vpn_user):
        self._vpn_user = vpn_user

    async def set_vpn_server(self, vpn_server):
        self._vpn_server = vpn_server

    async def run_cmdline(self, command_line):
        self._connect_failed = False
        try:
            await self.connection.async_run_command(command_line)
        except  Exception as e:
            self._connect_failed = True
            _LOGGER.error(e)

    async def reboot(self):
        if self._vpn_enabled:
            await self.run_cmdline("service restart_vpncall")
        else:
            await self.run_cmdline("reboot")

    async def run_command(self, command_line):
        await self.run_cmdline(command_line)

    async def set_port_forward(self, external_port, internal_port, protocol ,target_host):
        cmd = "nvram set vts_enable_x=1 ; nvram set vts_rulelist='<ruler>%s>%s>%s>%s>' ; "\
                   "nvram commit ; service restart_firewall" % (external_port,target_host,internal_port,protocol)
        await self.run_command(cmd)

    async def set_vpn_connect(self, server,name,password,protocol):
        cmd = "nvram set vpnc_pppoe_username= ; nvram set vpnc_pppoe_passwd= ; "\
                   "nvram set vpnc_proto=disable; nvram set wan0_proto=%s ; "\
                   "nvram set wan0_dnsenable_x=1 ; nvram set wan0_dhcpenable_x=1 ; "\
                   "nvram commit ; service restart_vpncall " % (protocol)
        if protocol != "dhcp":
            cmd = "nvram set vpnc_pppoe_username=%s; nvram set vpnc_pppoe_passwd=%s ; "\
                       "nvram set vpnc_proto=%s ; nvram set vpnc_heartbeat_x=%s ; "\
                       "nvram set vpnc_dnsenable_x=1 ; nvram set vpnc_clientlist='vpn>%s>%s>%s>%s'; "\
                       "nvram commit ; service restart_vpncall " % (name,password,protocol,server,
                       protocol.upper(),server,name,password)
        await self.run_cmdline(cmd)

    async def enable_wifi(self, type,enable):
        cmd = None

        if type == CONF_NAME_2GWIFI:
            cmd = "nvram set wl0_radio=%s ; nvram commit ; service restart_wireless" % (1 if enable else 0)
        elif type == CONF_NAME_5GWIFI:
            cmd = "nvram set wl1_radio=%s ; nvram commit ; service restart_wireless" % (1 if enable else 0)
        else:
            _LOGGER.error("can not find wifi type %s" % (type))

        if cmd:
            await self.run_cmdline(cmd)



async def async_setup(hass, config):
    """Set up the asusrouter component."""

    routers_conf = []

    if DOMAIN in config:
        routers_conf = config[DOMAIN][CONF_ROUTERS]

    routers = []
    for conf in routers_conf:
        router = AsusRouter(
            conf[CONF_HOST],
            conf[CONF_PORT],
            conf[CONF_NAME],
            conf[CONF_USERNAME],
            conf.get(CONF_PASSWORD, ""),
            conf.get(CONF_SSH_KEY, conf.get("pub_key", ""))
        )
        await router.set_add_attribute(config[DOMAIN][CONF_ADD_ATTR])
        await router.set_pub_mqtt(config[DOMAIN][CONF_PUB_MQTT])
        await router.set_sr_host_id(config[DOMAIN][CONF_SR_HOST_ID])

        routers.append(router)

    hass.data[DATA_ASUSWRT] = routers

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
                await device.run_command(call.data[CONF_COMMAND_LINE])
                await device.run_command(_SET_INITED_FLAG_CMD)

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

    async def _get_adbconn_target(msg):
        """Handle new MQTT messages."""
        param = json.loads(msg.payload)
        devices = hass.data[DOMAIN]

        for device in devices:
            if device.ssid == param['ssid']:
                try:
                    await device.set_port_forward(
                        5555,5555,'TCP',param['target']
                    )
                    num_list = device.host.split('.')
                    mqtt = hass.components.mqtt
                    msg = "{\"host\": \"%s\", \"domain\": \"%s\", \"public_ip\": \"%s\", \"port\": %s}" % (device.host, 
                        hass.states.get(device.sr_host_id).attributes.get('domain'), 
                        hass.states.get(device.sr_host_id).attributes.get('record'), 5000+int(num_list[3]))
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

        for device in devices:
            if device.vpn_user == param['vpn_user']:
                try:
                    mqtt = hass.components.mqtt
                    msg = "{\"user\": \"%s\",\"state\": \"inuse\", \"deviceid\": \"%s\", \"server\": \"%s\"}" % (device.vpn_user, 
                        device.device_name,device.vpn_server)
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

        if not offline_list:
            return

        for offline_item in offline_list:
            try:

                if offline_item['online'] > 5:
                    continue

                for device in devices:
                    device_id = device.device_name.split('_', 1)
                    if not device_id:
                        continue
                
                    if offline_item['id'][0:3] != device_id[1]:
                        continue

                    if device.public_ip == "":
                        continue
                    if device.public_ip == "0.0.0.0":
                        continue
                    
                    await device.reboot()
                    _LOGGER.warning("mqtt reboot device %s" % (device_id[1]))


            except  Exception as e:
                _LOGGER.error(e)


    async def _chage_vpn_user(msg):
        """Handle new MQTT messages."""
        param = json.loads(msg.payload)
        devices = hass.data[DOMAIN]
        
        try:
            for device in devices:
                device_id = device.device_name.split('_', 1)
                if not device_id:
                    continue
            
                if param['id'][0:3] != device_id[1]:
                    continue

                await device.set_vpn_connect(
                        param['server'],param['username'],
                        param['password'],param['protocol']
                    )

        except  Exception as e:
            _LOGGER.error(e)

    if config[DOMAIN][CONF_PUB_MQTT]:
        mqtt = hass.components.mqtt
        if mqtt:
            await mqtt.async_subscribe("router_monitor/global/commad/get_adbconn_target", _get_adbconn_target)
            await mqtt.async_subscribe("router_monitor/global/commad/get_vpn_account", _get_vpn_account)
            await mqtt.async_subscribe(MQTT_DEVICE_OFFLINE_TOPIC, _device_offline)
            await mqtt.async_subscribe(MQTT_CHANGE_VPNUSER_TOPIC, _chage_vpn_user)


    async def _enable_wifi(call):
        """Restart a router."""
        devices = hass.data[DOMAIN]
        for device in devices:
            if device.host == call.data[CONF_HOST] or call.data[CONF_HOST] == "ALL":
                await device.enable_wifi(call.data[CONF_TYPE_WIFI],call.data[CONF_ENABLE_WIFI])

    hass.services.async_register(
        DOMAIN, SERVICE_ENABLE_WIFI, _enable_wifi, schema=SERVICE_ENABLE_WIFI_SCHEMA
    )

    return True
          
