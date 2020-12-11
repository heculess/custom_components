"""Module for LedeWrt."""
import inspect
import logging
import math
import re

from collections import namedtuple
from .connection import SshConnection
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

from .const import DOMAIN_MQTT_PUB, CONF_NAME_2GWIFI, CONF_NAME_5GWIFI

_RX_COMMAND = "cat /sys/class/net/{}/statistics/rx_bytes"
_TX_COMMAND = "cat /sys/class/net/{}/statistics/tx_bytes"

CHANGE_TIME_CACHE_DEFAULT = 5  # Default 5s

class route_config:

    def __init__(self, conf=""):
        self.target = None
        self.gateway = None
        self.netmask = "255.255.255.255"
        self.interface = "lan"

        if conf :
            conf_list = conf.split('>>')
            if len(conf_list) > 1:
                self.interface = conf_list[1].lower()

                params = conf_list[0].split('>')
                if len(params) > 2:
                    self.gateway = params[2]
                    self.netmask = params[1]
                    self.target = params[0].strip('<')

class dns_config:

    def __init__(self, conf=""):
        self.name = None
        self.ip = None
        if conf :
            conf_list = conf.split(' ')
            if len(conf_list) > 1:
                self.name = conf_list[1]
                self.ip = conf_list[0]


class LedeWrt:
    """This is the interface class."""

    def __init__(self, host, name, port=None, username=None,
                 password=None, ssh_key=None):
        """Init function."""
        self._device_name = name
        self.connection = SshConnection(
            host, port, username, password, ssh_key)
        self._host = host
        self._connect_failed = False
        self._add_attribute = False
        self._client_number = 0
        self._download_speed = 0.0
        self._upload_speed = 0.0
        self._sr_host_id = None
        self._sr_caching_proxy = ""
        self._sr_host_proxy = ""
        self._init_dns = ""
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
        self.interface = "eth0"

        self._last_cmd = None

        self._rx_latest = None
        self._tx_latest = None
        self._latest_transfer_check = None
        self._cache_time = CHANGE_TIME_CACHE_DEFAULT
        self._trans_cache_timer = None
        self._transfer_rates_cache = None
        self._latest_transfer_data = 0, 0

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

    async def set_init_dns_line(self, command_line):
        self._init_dns = command_line

    async def set_device_state(self, state):
        self._device_state = state

    async def pub_device_state(self, name, state):
        self._hass.data[DOMAIN_MQTT_PUB].update_router_state(name,state)

    
    async def async_get_bytes_total(self, use_cache=True):
        """Retrieve total bytes (rx an tx) from ASUSWRT."""
        now = datetime.utcnow()
        if (
            use_cache
            and self._trans_cache_timer
            and self._cache_time > (now - self._trans_cache_timer).total_seconds()
        ):
            return self._transfer_rates_cache

        rx = await self.async_get_rx()
        tx = await self.async_get_tx()
        return rx, tx

    async def async_get_rx(self):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(
            _RX_COMMAND.format(self.interface)
        )
        return float(data[0]) if data[0] != "" else None

    async def async_get_tx(self):
        """Get current RX total given in bytes."""
        data = await self.connection.async_run_command(
            _TX_COMMAND.format(self.interface)
        )
        return float(data[0]) if data[0] != "" else None

    async def async_get_current_transfer_rates(self, use_cache=True):
        """Gets current transfer rates calculated in per second in bytes."""
        now = datetime.utcnow()
        data = await self.async_get_bytes_total(use_cache)
        if self._rx_latest is None or self._tx_latest is None:
            self._latest_transfer_check = now
            self._rx_latest = data[0]
            self._tx_latest = data[1]
            return self._latest_transfer_data

        time_diff = now - self._latest_transfer_check
        if time_diff.total_seconds() < 30:
            return self._latest_transfer_data

        if data[0] < self._rx_latest:
            rx = data[0]
        else:
            rx = data[0] - self._rx_latest
        if data[1] < self._tx_latest:
            tx = data[1]
        else:
            tx = data[1] - self._tx_latest
        self._latest_transfer_check = now

        self._rx_latest = data[0]
        self._tx_latest = data[1]

        self._latest_transfer_data = (
            math.ceil(rx / time_diff.total_seconds()) if rx > 0 else 0,
            math.ceil(tx / time_diff.total_seconds()) if tx > 0 else 0,
        )
        return self._latest_transfer_data
    
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
            return "wan"

        return "wan2"

    async def get_custom_dns(self):
        """Get router static routing."""
        dns_list = []
        try:

            conf_index = 0

            while True:
                
                dns = dns_config("")
                value_get = await self.run_cmdline(
                    "uci get dhcp.@domain[%s].name;" % conf_index)
                if self.connection.last_error:
                    break
                if value_get:
                    dns.name = value_get[0]

                value_get = await self.run_cmdline(
                    "uci get dhcp.@domain[%s].ip;" % conf_index)
                if value_get:
                    dns.ip = value_get[0]

                dns_list.append(dns)

                conf_index += 1

            return dns_list

        except  Exception as e:
            _LOGGER.error(e)
            return []

    async def need_update_dns(self, update_list):
        dns_list = await self.get_custom_dns()
        update_dns_list = list(update_list)

        for dns in dns_list:
           for update_dns in update_dns_list:
               if dns.name == update_dns.name \
                   and dns.ip == update_dns.ip:
                   update_dns_list.remove(update_dns)

        if len(update_dns_list) > 0:
            return True

        return False

    async def update_dns(self, new_dns_list):
        """Get router static routing."""
        try:
            if len(new_dns_list) == 0:
                return

            _LOGGER.debug("update new dns")
            await self.reset_network_setting("dhcp.@domain[0]")

            for dns in new_dns_list:
                add_dns = await self.run_cmdline('uci add dhcp domain')
                if not add_dns:
                    return

                await self.run_cmdline(
                    "uci set dhcp.%s.name='%s';""uci set network.%s.ip='%s'; uci commit;"\
                         % (add_dns[0],dns.name, add_dns[0], dns.ip))

            await self.run_cmdline("/etc/init.d/dnsmasq restart")

        except  Exception as e:
            _LOGGER.error(e)

    async def init_router(self):

        if self._last_cmd :
            _LOGGER.warning("retry command %s", self._last_cmd)
            await self.run_cmdline(self._last_cmd)

        if self._init_dns == "":
            return

        init_dns = []
        dns_list = self._init_dns.split(';')
        for dns in dns_list:
            init_dns.append(dns_config(dns.strip(' ')))

        if await self.need_update_dns(init_dns):
            await self.update_dns(init_dns)


    async def run_cmdline(self, command_line):
        self._connect_failed = False
        self._last_cmd = command_line
        try:
            run_result = await self.connection.async_run_command(command_line)
            self._last_cmd = None
            return run_result
        except  Exception as e:
            self._connect_failed = True
            _LOGGER.error(e)
            return None

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
            await self.run_cmdline("ubus call network.interface.vpn0 renew")
        else:
            await self.run_cmdline("reboot")

    async def disable_auto_dns(self):

        try:
    
            dnsenable = await self.connection.async_run_command(
                await self.get_wan_command("uci get network.%s.peerdns"))
            if not dnsenable:
                return
            if dnsenable[0] == "0":
                return

            wan_index = await self.get_wan_index()
            _LOGGER.info(" %s need to disable dns from remote" % (wan_index))

            cmd = "uci set network.%s.peerdns=0; "\
                "uci set network.%s.dns='%s 114.114.114.114'; "\
                "uci commit; /etc/init.d/network restart " % (wan_index,wan_index,
                self.host_to_gateway())

            await self.run_cmdline(cmd)

        except  Exception as e:
            _LOGGER.error(e)
            return
            
    async def run_command(self, command_line):
        await self.run_cmdline(command_line)

    async def set_port_forward(self, external_port, internal_port, protocol ,target_host):

        add_forward = await self.run_cmdline('uci add firewall redirect')
        if not add_forward or self.connection.last_error:
            return

        await self.run_cmdline(
            "uci set firewall.%s.target='DNAT';"\
                "uci set firewall.%s.src='%s';"\
                "uci set firewall.%s.dest='lan';"\
                "uci set firewall.%s.proto='%s';"\
                "uci set firewall.%s.src_dport='%s';"\
                "uci set firewall.%s.dest_ip='%s';"\
                "uci set firewall.%s.dest_port='%s';"\
                "uci set firewall.%s.name='ruler'; uci commit;"\
                    % (add_forward[0],add_forward[0],"wan",add_forward[0],add_forward[0],protocol.lower(),
                add_forward[0],external_port,add_forward[0],target_host,add_forward[0],internal_port,
                add_forward[0]))

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
            cmd = "uci set network.vpn0.server='%s';uci set network.vpn0.username='%s'"\
                    "uci set network.vpn0.password='%s';uci set network.vpn0.proto='%s'"\
                       "uci commit ; /etc/init.d/network restart" % (server,name,password,protocol)
        await self.run_cmdline(cmd)    

    async def enable_wifi(self, type, enable):
        cmd = None
        
        if type == CONF_NAME_2GWIFI:
            cmd = "uci set wireless.@wifi-iface[0].disabled=%s ; uci commit ; /etc/init.d/network restart" % (0 if enable else 1)
        elif type == CONF_NAME_5GWIFI:
            cmd = "uci set wireless.@wifi-iface[1].disabled=%s ; uci commit ; /etc/init.d/network restart" % (0 if enable else 1)
        else:
            _LOGGER.error("can not find wifi type %s" % (type))

        if cmd:
            await self.run_cmdline(cmd)

    async def map_clients(self, base_port, inner_port, protocol):
        
        map_list = ""
        port_index = 1

        client_list = []

        if protocol == "clear" :
            await self.reset_network_setting("firewall.@redirect[0]")
            return client_list

        for client in self._client_ip_list:

            map_port = base_port+port_index
            port_index += 1
            await self.set_port_forward(map_port,inner_port,protocol,client)

            client_list.append("%s:%s" % (self._host, map_port))
        
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

            route_index = 0

            while True:
                
                route = route_config("")
                value_get = await self.run_cmdline(
                    "uci get network.@route[%s].interface;" % route_index)
                if self.connection.last_error:
                    break
                if value_get:
                    route.interface = value_get[0]

                value_get = await self.run_cmdline(
                    "uci get network.@route[%s].target;" % route_index)
                if value_get:
                    route.target = value_get[0]

                value_get = await self.run_cmdline(
                    "uci get network.@route[%s].gateway;" % route_index)
                if value_get:
                    route.gateway = value_get[0]

                value_get = await self.run_cmdline(
                    "uci get network.@route[%s].netmask;" % route_index)
                if value_get:
                    route.netmask = value_get[0]

                rules.append(route)

                route_index += 1

            return rules

        except  Exception as e:
            _LOGGER.error(e)
            return []

    async def need_add_static_routing(self, add_target):
        rules_list = await self.get_static_routing()
        rulelist_add = list(add_target)

        for rule in rules_list:
           for rule_add in rulelist_add:
               if rule_add.interface == rule.interface \
                   and rule_add.target == rule.target \
                   and rule_add.gateway == rule.gateway \
                   and rule_add.netmask == rule.netmask:
                   rulelist_add.remove(rule_add)

        if len(rulelist_add) > 0:
            return True

        return False

    async def reset_network_setting(self, network_setting):
        """Reset router static routing."""
        try:
            go_next = True
            while go_next:

                run_error = await self.run_cmdline(
                    "uci delete %s; uci commit" % (network_setting))

                if self.connection.last_error:
                    go_next = False

        except  Exception as e:
            _LOGGER.error(e)

    async def set_static_routing(self, new_route_list):
        """Get router static routing."""
        try:
            if len(new_route_list) == 0:
                return rules

            _LOGGER.debug("update static routing")
            await self.reset_network_setting("network.@route[0]")

            for route in new_route_list:
                add_route = await self.run_cmdline('uci add network route')
                if not add_route:
                    return []

                await self.run_cmdline(
                    "uci set network.%s.interface='%s';"\
                        "uci set network.%s.target='%s';"\
                        "uci set network.%s.gateway='%s';"\
                        "uci set network.%s.netmask='%s'; uci commit;"\
                         % (add_route[0],route.interface,
                        add_route[0],route.target,add_route[0],route.gateway,
                        add_route[0],route.netmask))

        except  Exception as e:
            _LOGGER.error(e)
            return []
 

    async def update_static_routing(self):
        """Get static routing."""
        try:
            rulelist_add = []

            if self._sr_caching_proxy != "":
                rulelist_add.append(route_config(self._sr_caching_proxy))
            host_proxy = await self.get_host_proxy_rt_string()
            if host_proxy != "":
                rulelist_add.append(route_config(host_proxy))

            if len(rulelist_add) == 0:
                return    

            if await self.need_add_static_routing(rulelist_add):
                await self.set_static_routing(rulelist_add)

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