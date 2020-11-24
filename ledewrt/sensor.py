"""lederouter status sensors."""
import logging
import json
from datetime import datetime
from homeassistant.helpers.entity import Entity
from re import compile

from . import DATA_LEDEWRT

_LOGGER = logging.getLogger(__name__)

WAN_STATUS = 'ubus call network.interface.%s status'
_WIFI_NAME_CMD = 'uci get wireless.@wifi-iface[1].ssid'
_IP_REBOOT_CMD = 'reboot'
_CONNECT_STATE_WAN_CMD = 'nvram get %s_state_t'
_STATES_DISABLED_WIFI_5G_CMD = 'uci get wireless.@wifi-iface[1].disabled'

_WIFI_CHANNEL_5G_CMD = 'uci get wireless.@wifi-device[1].channel'

WIRELESS_CLIENTS_COMMAND = 'ubus call hostapd.wlan1 get_clients'
_ARP_LIST_COMMAND = 'cat /proc/net/arp'

_CONF_VPN_PROTO_DEFAULE = 'disable'

_IP_REGEX = compile(r'((?<![\.\d])(?:\d{1,3}\.){3}\d{1,3}(?![\.\d]))')


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the lederouter."""

    lederouters = hass.data[DATA_LEDEWRT]
    devices = []
    
    for router in lederouters:
        devices.append(LedeRouterSensor(router.device_name, router))
        if router.add_attribute:
            devices.append(RouterPublicIpSensor(router.device_name, router))
            devices.append(RouterHostSensor(router.device_name, router))
            devices.append(RouterClientCountSensor(router.device_name, router))
            devices.append(RouterInitStateSensor(router.device_name, router))
            devices.append(RouterDownloadSensor(router.device_name, router))
            devices.append(RouterUploadSensor(router.device_name, router))
            devices.append(RouterDownloadSpeedSensor(router.device_name, router))
            devices.append(RouterUploadSpeedSensor(router.device_name, router))
            devices.append(RouterVpnUsernameSensor(router.device_name, router))
            devices.append(RouterVpnServerSensor(router.device_name, router))
            devices.append(RouterVpnProtoSensor(router.device_name, router))

    devices.append(ClientCounterSensor(hass))
    devices.append(NetworkDownloadSpeedSensor(hass))
    devices.append(NetworkUploadSpeedSensor(hass))
    add_entities(devices, True)


class LedeSensor(Entity):
    """Representation of a lederouter."""

    def __init__(self, name, lederouter):
        """Initialize the router."""
        self._name = name
        self._connected = False
        self._initialized = False
        self._lederouter = lederouter
        self._wan_ip = "0.0.0.0"
        self._state = None
        self._rates = None
        self._ppoe_username = ""
        self._ppoe_heartbeat = ""
        self._ppoe_proto = _CONF_VPN_PROTO_DEFAULE
        self._5g_wifi = 0
        self._5g_wl_channel = "0"

    @property
    def state(self):
        """Return the state of the router."""
        return self._state

    async def get_wan_index(self):
        if await self._lederouter.get_wan2_state() == 0:
            return "0"

        return "1"

    async def async_run_command_to_line(self, command_line):
        return_lines = await self._lederouter.connection.async_run_command(
                command_line)
        if not return_lines:
            return None

        return_line = ""    
        for line in return_lines:
            return_line += line

        return return_line

    async def async_get_vpn_state(self):

        vpn_proto = await self._lederouter.connection.async_run_command("nvram get vpnc_proto")
        if vpn_proto:
            self._ppoe_proto = vpn_proto[0]

        if self._ppoe_proto == _CONF_VPN_PROTO_DEFAULE:
            await self._lederouter.set_vpn_enabled(False)
        else:
            await self._lederouter.set_vpn_enabled(True)


    async def async_get_wan_state(self):

        connect = await self._lederouter.connection.async_run_command(
            await self._lederouter.get_wan_command(_CONNECT_STATE_WAN_CMD))
        if not connect:
            return

        await self._lederouter.set_device_state(int(connect[0]))
        if connect[0] != '2':
            return

        if self._lederouter.vpn_enabled:
            vpn_state = await self._lederouter.connection.async_run_command("nvram get vpnc_state_t")
            if vpn_state:
                await self._lederouter.set_device_state(int(vpn_state[0]))

    async def async_get_vpn_client(self):
        if self._lederouter.vpn_enabled:
            usrname = await self._lederouter.connection.async_run_command(
                "nvram get vpnc_pppoe_username")
            if usrname:
                self._ppoe_username = usrname[0]
            heartbeat = await self._lederouter.connection.async_run_command(
                "nvram get vpnc_heartbeat_x")
            if heartbeat:
                self._ppoe_heartbeat = heartbeat[0]

    async def async_get_ppoe_vpn(self):
        usrname = await self._lederouter.connection.async_run_command(
            await self._lederouter.get_wan_command("nvram get %s_pppoe_username"))
        if usrname:
            self._ppoe_username = usrname[0]
        heartbeat = await self._lederouter.connection.async_run_command(
            await self._lederouter.get_wan_command("nvram get %s_heartbeat_x"))
        if heartbeat:
            self._ppoe_heartbeat = heartbeat[0]

    async def async_get_public_ip(self):
        """Get current public ip."""
        public_ip = None
        try:

            ip_content = await self._lederouter.connection.async_run_command('cat getip')
            if ip_content:
                ip_split = ip_content[0].split('：')
                if len(ip_split) > 2:
                    ip_regx = _IP_REGEX.findall(ip_split[1])
                    if ip_regx:
                        public_ip = "%s    %s" % (ip_regx[0],ip_split[2].replace('中国 ', ''))

            await self._lederouter.connection.async_run_command('rm getip')
            await self._lederouter.connection.async_run_command(
                "wget  -q -T 20 -b -O getip myip.ipip.net")

            if not public_ip:
                ip_content = await self._lederouter.connection.async_run_command('cat getip1')
                if ip_content:
                    ip_dict_regx = compile(r'{[^}]+}').findall(ip_content[0])
                    if ip_dict_regx:
                        ip_dict = ast.literal_eval(ip_dict_regx[0])
                        ip_from_dict = ip_dict.get('cip')
                        if ip_from_dict:
                            public_ip = "%s    %s" % (ip_from_dict,ip_dict.get('cname'))
            await self._lederouter.connection.async_run_command('rm getip1')
            await self._lederouter.connection.async_run_command(
                'wget -q -T 20 -b -O getip1 pv.sohu.com/cityjson?ie=utf-8')

            if not public_ip:
                ip_content = await self._lederouter.connection.async_run_command('cat getip2')
                if ip_content:
                    ip_regx = _IP_REGEX.findall(ip_content[0])
                    if ip_regx:
                        public_ip = ip_regx[0]
            await self._lederouter.connection.async_run_command('rm getip2')
            await self._lederouter.connection.async_run_command(
                'wget -q -T 20 -b -O getip2 members.3322.org/dyndns/getip')

        except  Exception as e:
            _LOGGER.error(e)

        if public_ip:
            await self._lederouter.set_public_ip(public_ip)
        else:
            await self._lederouter.set_public_ip("0.0.0.0")

    async def pub_data_mqtt(self):
        """Get trace router attribute to mqtt."""
        try:
            data_dict = self.device_state_attributes
            data_dict.update(state=self._lederouter.device_state)
            await self._lederouter.pub_device_state(self._name, data_dict)
        except  Exception as e:
            _LOGGER.error(e)

    async def get_wireless_clients(self):
        """Get dhcp clients."""
        try:
            connected_devices = await self.async_run_command_to_line(WIRELESS_CLIENTS_COMMAND)
            if  not connected_devices:
                await self._lederouter.set_client_number(0)
                return

            json_clients = json.loads(connected_devices)
            mac_clients = json_clients["clients"].keys()
            
            dict_arp = dict()
            arp_list = await self._lederouter.connection.async_run_command(
                _ARP_LIST_COMMAND)

            client_ip_list = []
            for arp in arp_list:

                for mac in mac_clients:
                    if arp.find(mac) >=0 :
                        ip_regx = _IP_REGEX.findall(arp)
                        if not ip_regx:
                            continue
                        client_ip_list.append(ip_regx[0])

            await self._lederouter.set_client_number(len(client_ip_list))
        except  Exception as e:
            _LOGGER.error(e)

    async def async_update(self):
        """Fetch status from router."""
        if self._lederouter.connect_failed:
            self._connected = False

        try:

            if not self._connected:
                await self._lederouter.connection.async_connect()

#            await self.async_get_vpn_state()
            wan_status = await self.async_run_command_to_line(
                await self._lederouter.get_wan_command(WAN_STATUS))
            if wan_status:
                status = json.loads(wan_status)
                self._wan_ip = status["ipv4-address"][0]["address"]

                wan_proto = status["proto"]
                self._lederouter.interface = status["device"]
#                await self.async_get_ppoe_vpn()

                self._rates = await self._lederouter.async_get_bytes_total()
                speed = await self._lederouter.async_get_current_transfer_rates()

                try:
                    if speed[0]:
                        await self._lederouter.set_download_speed(round(speed[0]/1000, 2))
                except  Exception as e:
                        await self._lederouter.set_download_speed(0.00)

                try:
                    if speed[1]:
                        await self._lederouter.set_upload_speed(round(speed[1]/1000, 2))
                except  Exception as e:
                       await self._lederouter.set_upload_speed(0.00)

#            await self.async_get_wan_state()
#            await self.async_get_vpn_client()
            await self._lederouter.update_static_routing()

            if not self._initialized:
                await self._lederouter.init_router()
                self._initialized = True

            ssid = await self._lederouter.connection.async_run_command(
                _WIFI_NAME_CMD)
            if ssid:
                await self._lederouter.set_ssid(ssid[0])

            wifi_disabled_5g = await self._lederouter.connection.async_run_command(
                _STATES_DISABLED_WIFI_5G_CMD)
            if wifi_disabled_5g:

                if wifi_disabled_5g[0].isdigit() and int(wifi_disabled_5g[0]) == 1:
                    self._5g_wifi = 0
                else:
                    self._5g_wifi = 1

            wl_channel = await self._lederouter.connection.async_run_command(
                _WIFI_CHANNEL_5G_CMD)
            if wl_channel:
                self._5g_wl_channel = wl_channel[0]

            if self._5g_wifi==1:
                await self._lederouter.set_wifi_enabled(True)
            else:
                await self._lederouter.set_wifi_enabled(False)

            await self.get_wireless_clients()

            self._connected = True
            await self.async_get_public_ip()

            await self.pub_data_mqtt()

#            await self._lederouter.set_vpn_user(self._ppoe_username)
#            await self._lederouter.set_vpn_server(self._ppoe_heartbeat)

        except  Exception as e:
            self._connected = False
            await self._lederouter.set_public_ip("0.0.0.0")
            if self._lederouter.connect_failed:
                await self._lederouter.set_device_state(0)
            _LOGGER.error(e)


class LedeRouterSensor(LedeSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "lederouter_%s" % (self._name)

    @property
    def wan_ip(self):
        """Return the wan ip of router."""
        return self._wan_ip

    @property
    def download(self):
        """Return the total download."""
        try:
            if self._rates[0]:
                return round(self._rates[0]/1000000000, 2)
        except  Exception as e:
            return 0

    @property
    def upload(self):
        """Return the total upload."""
        try:
            if self._rates[1]:
                return round(self._rates[1]/1000000000, 2)
        except  Exception as e:
            return 0
      
    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {
            'initialized': self._initialized,
            'wan_ip': self._wan_ip,
            'public_ip': self._lederouter.public_ip,
            'interface': self._lederouter.interface,
            'download': self.download,
            'upload': self.upload,
            'download_speed': self._lederouter.download_speed,
            'upload_speed': self._lederouter.upload_speed,
            'connect_state': self._connected,
            'ssid': self._lederouter.ssid,
            'host': self._lederouter.host,
            'client_number': self._lederouter.client_number,
            '5G_wifi': self._5g_wifi,
            '5G_wifi_channel': self._5g_wl_channel,
            'vpn_username': self._ppoe_username,
            'vpn_server': self._ppoe_heartbeat,
            'vpn_proto': self._ppoe_proto,
        }

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._lederouter.device_state


class RouterWanIpSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_wan_ip" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:ip"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._wan_ip

class RouterPublicIpSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_public_ip" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:ip-network"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._lederouter.public_ip

class RouterHostSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_host" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:ip"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._lederouter.host

class RouterClientCountSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_client_count" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:magnify-plus"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return " "

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._lederouter.client_number

class RouterInitStateSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_init_state" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:check-circle"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._initialized

class RouterDownloadSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_download" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:chart-pie"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "GiB"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state =  super().download

class RouterUploadSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_upload" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:chart-pie"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "GiB"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        setattr(self, "_icon", 'mdi:chart-pie')
        self._state =  super().upload

class RouterDownloadSpeedSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_download_speed" % (self._name)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "KiB/s"

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:download"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state =  self._lederouter.download_speed

class RouterUploadSpeedSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_upload_speed" % (self._name)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "KiB/s"

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:upload"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state =  self._lederouter.upload_speed

class RouterVpnUsernameSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_vpn_username" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:account"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._ppoe_username

class RouterVpnServerSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_vpn_server" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:sitemap"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._ppoe_heartbeat

class RouterVpnProtoSensor(LedeRouterSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "%s_vpn_proto" % (self._name)

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return "mdi:protocol"

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {}

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._ppoe_proto

class ClientCounterSensor(Entity):
    def __init__(self, hass):
        """Initialize the router."""
        self._hass = hass
        self._state = "0"

    @property
    def name(self):
        return "devices_counter"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return " "

    def get_devices_count(self):
        count_total = 0
        try:
            devices = self._hass.data[DATA_LEDEWRT]
            for device in devices:
                count_total += device.client_number

            return count_total
        except  Exception as e:
            _LOGGER.error(e)
            return dict()

    async def async_update(self):

        try:
            self._state = "%s" % self.get_devices_count()
        except  Exception as e:
            _LOGGER.error(e)
            self._state = "not count"

class NetworkUploadSpeedSensor(Entity):
    def __init__(self, hass):
        """Initialize the router."""
        self._hass = hass
        self._state = "0"

    @property
    def name(self):
        return "network_upload_monitor"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "KiB/s"

    def get_speed(self):
        count_total = 0.0
        try:
            devices = self._hass.data[DATA_LEDEWRT]
            for device in devices:
                count_total += device.upload_speed

            return count_total
        except  Exception as e:
            _LOGGER.error(e)
            return dict()

    async def async_update(self):

        try:
            self._state = "%s" % round(self.get_speed(),2)
        except  Exception as e:
            _LOGGER.error(e)
            self._state = "not count"

class NetworkDownloadSpeedSensor(Entity):
    def __init__(self, hass):
        """Initialize the router."""
        self._hass = hass
        self._state = "0"

    @property
    def name(self):
        return "network_download_monitor"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "KiB/s"

    def get_speed(self):
        count_total = 0.0
        try:
            devices = self._hass.data[DATA_LEDEWRT]
            for device in devices:
                count_total += device.download_speed

            return count_total
        except  Exception as e:
            _LOGGER.error(e)
            return dict()

    async def async_update(self):

        try:
            self._state = "%s" % round(self.get_speed(),2)
        except  Exception as e:
            _LOGGER.error(e)
            self._state = "not count"
        
      

    
