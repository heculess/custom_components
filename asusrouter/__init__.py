"""Support for ASUSROUTER devices."""
import logging
import json
import voluptuous as vol

from homeassistant.const import (
    ATTR_NOW,

    CONF_NAME,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_PORT,

    EVENT_TIME_CHANGED,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.util import dt as dt_util
from aioasuswrt.asuswrt import AsusWrt
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

CONF_PUB_KEY = "pub_key"
CONF_SENSORS = "sensors"
CONF_SSH_KEY = "ssh_key"
CONF_USE_TELNET = "use_telnet"
CONF_ADD_ATTR = "add_attribute"
CONF_PUB_MQTT = "pub_mqtt"
CONF_SR_HOST_ID = "sr_host_id"
CONF_SR_CACHING_PROXY = "sr_caching_proxy"
CONF_SR_HOST_PROXY = "sr_host_proxy"
CONF_MAX_OFFINE_SETTING = "max_offline_setting"
CONF_INIT_COMMAND = "init_command"
CONF_SSID = "ssid"
CONF_TARGETHOST = "target_host"
CONF_PORT_EXTER = "external_port"
CONF_PORT_INNER = "internal_port"
CONF_PORT_BASE = "base_port"
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
DOMAIN_MQTT_PUB = "asusrouter_mqtt_pub"
CONF_ROUTERS = "routers"
DATA_ASUSWRT = DOMAIN
DEFAULT_SSH_PORT = 22
DEFAULT_MAX_OFFINLE = 5

CMD_MQTT_TOPIC = "router_monitor/global/commad/on_get_adbconn_target"
MQTT_VPN_ACCOUNT_TOPIC = "router_monitor/global/commad/on_get_vpn_account"
MQTT_DEVICE_OFFLINE_TOPIC = "router_monitor/global/commad/device_offline"
MQTT_CHANGE_VPNUSER_TOPIC = "router_monitor/global/commad/change_vpn_account"
MQTT_MAP_CLIENT_TOPIC = "router_monitor/global/commad/map_all_client"
MQTT_CMD_UPDATE_STATES_TOPIC = "router_monitor/global/commad/update_states"
MQTT_STATES_UPDATE_TOPIC = "router_monitor/global/states/update"
MQTT_STATES_MAP_CLIENT_TOPIC = "router_monitor/global/states/map_client"
MQTT_STATES_NETWORK_TOPIC = "router_monitor/global/network/update"

SERVICE_REBOOT = "reboot"
SERVICE_RUNCOMMAND = "run_command"
SERVICE_INITDEVICE = "init_device"
SERVICE_SET_PORT_FORWARD = "set_port_forward"
SERVICE_SET_VPN_CONNECT = "set_vpn_connect"
SERVICE_ENABLE_WIFI = "enable_wifi"
SERVICE_MAP_CLIENT = "map_all_clients"

_SET_INITED_FLAG_CMD = "touch /etc/inited ; service restart_firewall"

NETWORK_STATE_DOWNLOAD = "download"
NETWORK_STATE_UPLOAD = "upload"
NETWORK_STATE_DOWNLOAD_SPEED = "download_speed"
NETWORK_STATE_UPLOAD_SPEED = "upload_speed"

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
                vol.Optional(CONF_INIT_COMMAND, default=""): cv.string,
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

class AsusWrtMqttPub:
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


class AsusRouter(AsusWrt):
    """interface of a asusrouter."""

    def __init__(self, host, port, use_telnet, devicename, username, password, ssh_key):
        """Init function."""
        super().__init__(host, port, use_telnet, username, password, ssh_key)
        self._device_name = devicename
        self._host = host
        self._connect_failed = False
        self._add_attribute = False
        self._client_number = 0
        self._download_speed = 0.0
        self._upload_speed = 0.0
        self._sr_host_id = None
        self._sr_caching_proxy = ""
        self._sr_host_proxy = ""
        self._init_command = ""
        self._vpn_enabled = False
        self._vpn_user = False
        self._vpn_server = False
        self._public_ip = "0.0.0.0"
        self._ssid = ""
        self._last_vpn_restart_time = None
        self._max_offline_setting = None
        self._wifi_enabled = False
        self._hass = None
        self._device_sn = None
        self._device_state = 0
        self._client_ip_list = []

        self._last_cmd = None

        serial_number = self._device_name.split('_', 1)
        if len(serial_number) > 1:
            self._device_sn = serial_number[1]
        

    @property
    def device_name(self):
        """Return the device name of the router."""
        return self._device_name

    @property
    def device_sn(self):
        """Return the serial number of the router."""
        if self._device_sn :
            return self._device_sn
        return "sn_%s" % (self._device_name)

    @property
    def host(self):
        """Return the host ip of the router."""
        return self._host

    @property
    def connect_failed(self):
        """Return if the router is connected failed."""
        return self._connect_failed

    @property
    def client_number(self):
        """Return if the mqtt is enabled"""
        return  self._client_number

    @property
    def download_speed(self):
        """Return the download speed."""
        return self._download_speed

    @property
    def upload_speed(self):
        """Return the upload speed."""
        return self._upload_speed

    @property
    def public_ip(self):
        """Return the public ip of the router."""
        return  self._public_ip

    @property
    def add_attribute(self):
        """Return if auto add the attribute of the router."""
        return self._add_attribute

    @property
    def sr_host_id(self):
        """Return the server room ip device id."""
        return  self._sr_host_id

    @property
    def vpn_enabled(self):
        """Return if the router vpn is enabled."""
        return self._vpn_enabled

    @property
    def vpn_user(self):
        """Return the vpn user of the router."""
        return self._vpn_user

    @property
    def vpn_server(self):
        """Return the vpn server of the router."""
        return self._vpn_server

    @property
    def ssid(self):
        """Return the ssid of the router."""
        return self._ssid

    @property
    def device_state(self):
        """Return the state of the router."""
        return self._device_state

    @property
    def client_ip_list(self):
        """Return the client list of the router."""
        return self._client_ip_list

    @property
    def wifi_enabled(self):
        """Return if wifi is enabled."""
        return self._wifi_enabled

    async def set_ssid(self, ssid):
        self._ssid = ssid

    async def set_hass(self, hass):
        self._hass = hass

    async def set_wifi_enabled(self, enabled):
        self._wifi_enabled = enabled

    async def set_add_attribute(self, add_attribute):
        self._add_attribute = add_attribute

    async def set_client_number(self, number):
        self._client_number = number

    async def set_download_speed(self, speed):
        self._download_speed = speed

    async def set_upload_speed(self, speed):
        self._upload_speed = speed

    async def set_sr_host_id(self, sr_host_id):
        self._sr_host_id = sr_host_id

    async def set_caching_proxy(self, sr_caching_proxy):
        self._sr_caching_proxy = sr_caching_proxy

    async def set_sr_host_proxy(self, sr_host_proxy):
        self._sr_host_proxy = sr_host_proxy

    async def set_vpn_enabled(self, vpn_enable):
        self._vpn_enabled = vpn_enable

    async def set_public_ip(self, public_ip):
        self._public_ip = public_ip

    async def set_vpn_user(self, vpn_user):
        self._vpn_user = vpn_user

    async def set_vpn_server(self, vpn_server):
        self._vpn_server = vpn_server

    async def set_client_ip_list(self, ip_list):
        self._client_ip_list = ip_list

    async def set_max_offline_setting(self, max_offline_setting):
        self._max_offline_setting = max_offline_setting

    async def set_init_command_line(self, command_line):
        self._init_command = command_line

    async def set_device_state(self, state):
        self._device_state = state

    async def pub_device_state(self, name, state):
        self._hass.data[DOMAIN_MQTT_PUB].update_router_state(name,state)

    def get_max_offine(self, hass):
        """get max offine."""
        if not self._max_offline_setting:
            return DEFAULT_MAX_OFFINLE

        if self._max_offline_setting == "":
            return DEFAULT_MAX_OFFINLE

        item = hass.states.get(self._max_offline_setting)
        if not item:
            return DEFAULT_MAX_OFFINLE
        return int(float(item.state))

    def match_device_id(self, device_id):
        """return if match the device_id."""
        device_id = device_id.strip()

        if not device_id:
            return False

        if device_id == self._device_name:
            return True

        if not self._device_sn:
            return False

        if device_id[0].isdigit():
            if device_id[0:3] == self._device_sn:
                return True 

        return False

    async def get_wan_command(self, lines):
        return lines % (await self.get_wan_index())

    async def get_wan_index(self):
        if await self.get_wan2_state() == 0:
            return "wan0"

        return "wan1"

    async def init_router(self):

        if self._last_cmd :
            _LOGGER.warning("retry command %s", self._last_cmd)
            await self.run_cmdline(self._last_cmd)

        if self._init_command == "":
            return

        await self.init_device(self._init_command)

    async def init_device(self, command_line):
        await self.run_command(command_line)
        await self.run_command(_SET_INITED_FLAG_CMD)

    async def run_cmdline(self, command_line):
        self._connect_failed = False
        self._last_cmd = command_line
        try:
            await self.connection.async_run_command(command_line)
            self._last_cmd = None
        except  Exception as e:
            self._connect_failed = True
            _LOGGER.error(e)

    def only_reboot_vpn(self):
        """Return if only reboot vpn service."""
        if self._vpn_enabled:

            now = datetime.utcnow()
            if not self._last_vpn_restart_time:
                self._last_vpn_restart_time = now
                return True
            
            interval = (now - self._last_vpn_restart_time).total_seconds()
            if interval < 300:
                return True
            if interval > 600:     
                self._last_vpn_restart_time = now
                return True         

        self._last_vpn_restart_time = None
        return False

    def host_to_gateway(self):

        num_list = self._host.split('.')
        if len(num_list) != 4:
            return "192.168.2.1"

        return "%s.%s.%s.1" % (num_list[0],num_list[1],num_list[2])

    async def reboot(self):
        if self.only_reboot_vpn():
            await self.run_cmdline("service restart_vpncall")
        else:
            await self.run_cmdline("reboot")

    async def disable_auto_dns(self):

        try:
    
            dnsenable = await self.connection.async_run_command(
                await self.get_wan_command("nvram get %s_dnsenable_x"))
            if not dnsenable:
                return
            if dnsenable[0] == "0":
                return

            wan_index = await self.get_wan_index()
            _LOGGER.info(" %s need to disable dns from remote" % (wan_index))

            cmd = "nvram set %s_dnsenable_x=0 ; "\
                "nvram set %s='%s 114.114.114.114'; "\
                "nvram set %s_dns1_x='%s'; "\
                "nvram set %s_dns2_x='114.114.114.114'; "\
                "nvram commit ; service restart_wan" % (wan_index,wan_index,self.host_to_gateway(),wan_index,
                    self.host_to_gateway(),wan_index)

            await self.run_cmdline(cmd)

        except  Exception as e:
            _LOGGER.error(e)
            return
            
    async def run_command(self, command_line):
        await self.run_cmdline(command_line)

    async def set_port_forward(self, external_port, internal_port, protocol ,target_host):
        cmd = "nvram set vts_enable_x=1 ; nvram set vts_rulelist='<ruler>%s>%s>%s>%s>' ; "\
                   "nvram commit ; service restart_firewall" % (external_port,target_host,internal_port,protocol)
        await self.run_command(cmd)

    def vpn_protocol_valid(self,protocol):
        """Return if vpn protocol is correct."""
        if protocol == "dhcp":
            return True
        if protocol == "pptp":
            return True
        if protocol == "l2tp":
            return True
        return False

    async def set_vpn_connect(self, server,name,password,protocol):

        if not self.vpn_protocol_valid(protocol):
            _LOGGER.error("set a wrong vpn protocol : %s" % (protocol))
            return
            
        wan_index = await self.get_wan_index()
        cmd = "nvram set vpnc_pppoe_username= ; nvram set vpnc_pppoe_passwd= ; "\
                   "nvram set vpnc_proto=disable; nvram set %s_proto=%s ; "\
                   "nvram set %s_dnsenable_x=1 ; nvram set %s_dhcpenable_x=1 ; "\
                   "nvram commit ; service restart_vpncall ; service restart_wan" % (wan_index,
                   protocol,wan_index,wan_index)
        if protocol != "dhcp":
            cmd = "nvram set vpnc_pppoe_username=%s; nvram set vpnc_pppoe_passwd=%s ; "\
                       "nvram set vpnc_proto=%s ; nvram set vpnc_heartbeat_x=%s ; "\
                       "nvram set vpnc_dnsenable_x=1 ; nvram set vpnc_clientlist='vpn>%s>%s>%s>%s'; "\
                       "nvram commit ; service restart_vpncall ; service restart_wan" % (name,password,protocol,server,
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

    async def map_clients(self, base_port, inner_port, protocol):
        
        map_list = ""
        port_index = 1

        client_list = []

        if protocol == "clear" :
            await self.run_cmdline("nvram set vts_rulelist= ; nvram commit ; service restart_firewall")
            return client_list

        for client in self._client_ip_list:

            map_port = base_port+port_index

            map_value = "<ruler>%s>%s>%s>%s>" % (map_port,client,inner_port,protocol)
            port_index += 1
            map_list += map_value

            client_list.append("%s:%s" % (self._host, map_port))

        cmd = "nvram set vts_enable_x=1 ; nvram set vts_rulelist='%s' ; nvram commit ; service restart_firewall" % (map_list)
        if cmd:
            await self.run_cmdline(cmd)
        
        return client_list

    async def get_host_proxy_rt_string(self):
        """Get host proxy static routing string."""
        try:
    
            if self._sr_host_proxy == "":
                return ""

            if not self._hass:
                return ""

            sr_host = self._hass.states.get(self._sr_host_id)
            if not sr_host:
                _LOGGER.debug("sr host is not found")
                return ""

            host_ip = sr_host.attributes.get('record')
            if host_ip == "":
                return ""

            return self._sr_host_proxy % (host_ip)

        except  Exception as e:
            _LOGGER.error(e)
            return ""

    async def get_static_routing(self):
        """Get router static routing."""
        rules = []
        try:
    
            rulelist = await self.connection.async_run_command("nvram get sr_rulelist")
            if not rulelist:
                return rules

            rules_split = rulelist[0].split('<')

            for rule in rules_split:
                if rule.find('>') > 0:
                    rules.append("<" + rule)

            return rules

        except  Exception as e:
            _LOGGER.error(e)
            return []

    async def need_add_static_routing(self, add_target):
        rules_list = await self.get_static_routing()
        rulelist_add = list(add_target)

        for rule in rules_list:
            for rule_add in rulelist_add:
                if rule_add == rule:
                    rulelist_add.remove(rule_add)
                    break

        if len(rulelist_add) > 0:
            return True

        return False

    async def set_static_routing(self, new_routing):
        """Get router static routing."""
        try:
    
            if new_routing == "":
                return rules

            _LOGGER.info("update static routing : " + new_routing)

            await self.run_cmdline(
                "nvram set sr_enable_x=1 ; nvram set sr_rulelist='%s' ; nvram commit" % (new_routing))

        except  Exception as e:
            _LOGGER.error(e)
            return []
 

    async def update_static_routing(self):
        """Get static routing."""
        try:
            rulelist_add = []

            if self._sr_caching_proxy != "":
                rulelist_add.append(self._sr_caching_proxy)
            host_proxy = await self.get_host_proxy_rt_string()
            if host_proxy != "":
                rulelist_add.append(host_proxy)

            if len(rulelist_add) == 0:
                return    
                    
            if await self.need_add_static_routing(rulelist_add):
                rule_add_string = ""
                for rule_add in rulelist_add:
                    rule_add_string += rule_add

                await self.set_static_routing(rule_add_string)

        except  Exception as e:
            _LOGGER.error(e)

    async def get_wan2_state(self):
        """Get router wan2 status."""
        try:
            status = await self.connection.async_run_command("nvram get wans_dualwan")
            if not status:
                return 0

            wan_list = status[0].split(' ')
            if len(wan_list) < 2:
                return 0

            if wan_list[1] != "none":
                return 1

            return 0

        except  Exception as e:
            _LOGGER.error(e)
            return 0



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
            conf[CONF_USE_TELNET],
            conf[CONF_NAME],
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
        await router.set_init_command_line(config[DOMAIN][CONF_INIT_COMMAND])

        routers.append(router)

    hass.data[DATA_ASUSWRT] = routers
    hass.data[DOMAIN_MQTT_PUB] = AsusWrtMqttPub(hass,config[DOMAIN][CONF_PUB_MQTT])

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
          
