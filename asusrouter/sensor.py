"""Asusrouter status sensors."""
import logging
import math
import ast
import json
from datetime import datetime
from re import compile
from homeassistant.helpers.entity import Entity
from . import AsusRouter
from . import DATA_ASUSWRT

_LOGGER = logging.getLogger(__name__)

_IP_WAN_CMD = 'nvram get wan0_ipaddr'
_WIFI_NAME_CMD = 'nvram get wl1_ssid'
_IP_REBOOT_CMD = 'reboot'
_CONNECT_STATE_WAN_CMD = 'nvram get wan0_state_t'
_STATES_WIFI_5G_CMD = 'nvram get wl1_radio'
_STATES_WIFI_2G_CMD = 'nvram get wl0_radio'

_WIFI_CHANNEL_5G_CMD = 'wl -i eth2 status ; iwlist ath1 channel'
_WIFI_CHANNEL_2G_CMD = 'wl -i eth1 status ; wlanconfig ath0 list'

_ROUTER_WAN_PROTO_COMMAND = 'nvram get wan0_proto'

_ROUTER_IS_INITED_COMMAND = 'find /etc/inited'
_RET_IS_INITED = '/etc/inited'

_ROUTER_RX_COMMAND = 'cat /sys/class/net/ppp0/statistics/rx_bytes'
_ROUTER_TX_COMMAND = 'cat /sys/class/net/ppp0/statistics/tx_bytes'

_DHCP_CLIENTS_COMMAND = 'cat /var/lib/misc/dnsmasq.leases'
_ARP_LIST_COMMAND = 'arp -n'

_CONF_VPN_PROTO_DEFAULE = 'disable'

CHANGE_TIME_CACHE_DEFAULT = 5  # Default 60s

_IP_REGEX = compile(r'((?<![\.\d])(?:\d{1,3}\.){3}\d{1,3}(?![\.\d]))')

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the asusrouter."""

    asusrouters = hass.data[DATA_ASUSWRT]
    mqtt = hass.components.mqtt
    devices = []
    for router in asusrouters:
        devices.append(AsuswrtRouterSensor(router.device_name, router, mqtt))
        if router.add_attribute:
            devices.append(RouterWanIpSensor(router.device_name, router))
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

    add_entities(devices, True)


class AsuswrtSensor(Entity):
    """Representation of a asusrouter."""

    def __init__(self, name, asusrouter, mqtt = None):
        """Initialize the router."""
        self._name = name
        self._connected = False
        self._initialized = False
        self._asusrouter = asusrouter
        self._reboot = asusrouter.reboot
        self._wan_ip = "0.0.0.0"
        self._state = None
        self._rates = 0.0
        self._speed = 0.0
        self._rx_latest = None
        self._tx_latest = None
        self._cache_time = CHANGE_TIME_CACHE_DEFAULT
        self._latest_transfer_check = None
        self._transfer_rates_cache = None
        self._trans_cache_timer = None
        self._latest_transfer_data = 0, 0
        self._ppoe_username = ""
        self._ppoe_heartbeat = ""
        self._ppoe_proto = _CONF_VPN_PROTO_DEFAULE
        self._mqtt = mqtt
        self._5g_wifi = 0
        self._2g_wifi = 0
        self._5g_wl_channel = "0"
        self._2g_wl_channel = "0"
        self._client_number = 0

    @property
    def state(self):
        """Return the state of the router."""
        return self._state

    def get_channel_from_line(self, lines):
        if not lines:
            return "0"

        line_size = len(lines)
        if line_size < 4:
            return "0"

        if lines[0].find("SSID:") >= 0:
            lines = lines[1].split("	")
            for line in lines:
                params = line.split(':')
                if len(params) > 1 and params[0] == "Channel":
                    return params[1].strip()
        else:
            for line in lines:
                if line.find("Current Frequency") > 0:
                    freq_regx = compile(r'(?<=\(Channel )(.+?)(?=\))').findall(line)
                    if freq_regx:
                        return freq_regx[0]

        return "0"

    async def async_get_bytes_total(self):
        """Retrieve total bytes (rx an tx) from ASUSROUTER."""
        now = datetime.utcnow()
        if self._trans_cache_timer and self._cache_time > \
                (now - self._trans_cache_timer).total_seconds():
            return self._transfer_rates_cache

        rx = await self.async_get_rx()
        tx = await self.async_get_tx()
        return rx, tx
        
    async def async_get_rx(self):
        """Get current RX total given in bytes."""
        data = await self._asusrouter.connection.async_run_command(_ROUTER_RX_COMMAND)
        if data and data[0].isdigit():
            return int(data[0])
        return 0

    async def async_get_tx(self):
        """Get current RX total given in bytes."""
        data = await self._asusrouter.connection.async_run_command(_ROUTER_TX_COMMAND)
        if  data and data[0].isdigit():
            return int(data[0])
        return 0
        
    async def async_get_current_transfer_rates(self):
        """Gets current transfer rates calculated in per second in bytes."""
        now = datetime.utcnow()
        data = await self.async_get_bytes_total()
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
            math.ceil(tx / time_diff.total_seconds()) if tx > 0 else 0)
        return self._latest_transfer_data

    async def async_get_vpn_state(self):

        vpn_proto = await self._asusrouter.connection.async_run_command("nvram get vpnc_proto")
        if vpn_proto:
            self._ppoe_proto = vpn_proto[0]

        if self._ppoe_proto == _CONF_VPN_PROTO_DEFAULE:
            await self._asusrouter.set_vpn_enabled(False)
        else:
            await self._asusrouter.set_vpn_enabled(True)


    async def async_get_wan_state(self):

        connect = await self._asusrouter.connection.async_run_command(
            _CONNECT_STATE_WAN_CMD)
        if not connect:
            return

        await self._asusrouter.set_device_state(connect[0])
        if connect[0] != '2':
            return

        if self._asusrouter.vpn_enabled:
            vpn_state = await self._asusrouter.connection.async_run_command("nvram get vpnc_state_t")
            if vpn_state:
                await self._asusrouter.set_device_state(vpn_state[0])

    async def async_get_vpn_client(self):
        if self._asusrouter.vpn_enabled:
            usrname = await self._asusrouter.connection.async_run_command(
                "nvram get vpnc_pppoe_username")
            if usrname:
                self._ppoe_username = usrname[0]
            heartbeat = await self._asusrouter.connection.async_run_command(
                "nvram get vpnc_heartbeat_x")
            if heartbeat:
                self._ppoe_heartbeat = heartbeat[0]

    async def async_get_ppoe_vpn(self):
        usrname = await self._asusrouter.connection.async_run_command(
            "nvram get wan0_pppoe_username")
        if usrname:
            self._ppoe_username = usrname[0]
        heartbeat = await self._asusrouter.connection.async_run_command(
            "nvram get wan0_heartbeat_x")
        if heartbeat:
            self._ppoe_heartbeat = heartbeat[0]

    async def async_get_public_ip(self):
        """Get current public ip."""
        public_ip = None
        try:

            ip_content = await self._asusrouter.connection.async_run_command('cat getip')
            if ip_content:
                for content in ip_content:
                    ip_regx = compile(r'(?<=<code>)[\s\S]*?(?=<\/code>)').findall(content)
                    if ip_regx:
                        public_ip = "%s    %s" % (ip_regx[0],ip_regx[1])
            await self._asusrouter.connection.async_run_command('rm getip')
            await self._asusrouter.connection.async_run_command(
                "wget  -q --no-check-certificate -b --header='User-Agent: \
                Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko' -O getip ip.cn")

            if not public_ip:
                ip_content = await self._asusrouter.connection.async_run_command('cat getip1')
                if ip_content:
                    ip_dict_regx = compile(r'{[^}]+}').findall(ip_content[0])
                    if ip_dict_regx:
                        ip_dict = ast.literal_eval(ip_dict_regx[0])
                        ip_from_dict = ip_dict.get('cip')
                        if ip_from_dict:
                            public_ip = "%s    %s" % (ip_from_dict,ip_dict.get('cname'))
            await self._asusrouter.connection.async_run_command('rm getip1')
            await self._asusrouter.connection.async_run_command(
                'wget -q -b -O getip1 pv.sohu.com/cityjson?ie=utf-8')

            if not public_ip:
                ip_content = await self._asusrouter.connection.async_run_command('cat getip2')
                if ip_content:
                    ip_regx = _IP_REGEX.findall(ip_content[0])
                    if ip_regx:
                        public_ip = ip_regx[0]
            await self._asusrouter.connection.async_run_command('rm getip2')
            await self._asusrouter.connection.async_run_command(
                'wget -q -b -O getip2 members.3322.org/dyndns/getip')

        except  Exception as e:
            _LOGGER.error(e)

        if public_ip:
            await self._asusrouter.set_public_ip(public_ip)
        else:
            await self._asusrouter.set_public_ip("0.0.0.0")

    async def pub_data_mqtt(self):
        """Get trace router attribute to mqtt."""
        if not self._asusrouter.pub_mqtt:
            return

        if not self._mqtt:
            _LOGGER.error("can not find mqtt")
            return

        try:
            topic = "router_monitor/%s/states" % (self._name)
            data_dict = self.device_state_attributes
            if self._asusrouter.device_state.isdigit():
                data_dict.update(state=int(self._asusrouter.device_state))
            data_pub = json.dumps(data_dict)
            self._mqtt.publish(topic, data_pub)

        except  Exception as e:
            _LOGGER.error(e)

    async def get_dhcp_clients(self):
        """Get dhcp clients."""
        try:
            connected_devices = await self._asusrouter.connection.async_run_command(
                _DHCP_CLIENTS_COMMAND)
            if  not connected_devices:
                self._client_number = 0
                return

            dict_arp = dict()
            arp_list = await self._asusrouter.connection.async_run_command(
                _ARP_LIST_COMMAND)
            for arp in arp_list:
                arp_info = arp.split(' ')
                if len(arp_info) < 5:
                    continue
                dict_arp[arp_info[1].strip("()")] = arp_info[3]

            client_count  = 0
            for device in connected_devices:
                dhcp_data = device.split(' ')     
                ip_regx = _IP_REGEX.findall(device)
                if not ip_regx:
                    continue

                if ip_regx[0] in dict_arp:
                    client_count  += 1

            self._client_number = client_count
        except  Exception as e:
            _LOGGER.error(e)

    async def async_update(self):
        """Fetch status from router."""
        if self._asusrouter.connect_failed:
            self._connected = False

        try:

            if not self._connected:
                await self._asusrouter.connection.async_connect()

            inited = await self._asusrouter.connection.async_run_command(
                _ROUTER_IS_INITED_COMMAND)
            if not inited:
                return

            if inited[0] == _RET_IS_INITED:
                self._initialized = True
            else:
                self._initialized = False

            await self.async_get_vpn_state()

            lines = await self._asusrouter.connection.async_run_command(_IP_WAN_CMD)
            if lines:
                self._wan_ip = lines[0]

            await self.async_get_wan_state()
            await self.async_get_vpn_client()
            await self._asusrouter.update_static_routing()

            if not self._initialized:
                await self._asusrouter.init_router()

            ssid = await self._asusrouter.connection.async_run_command(
                _WIFI_NAME_CMD)
            if ssid:
                await self._asusrouter.set_ssid(ssid[0])

            wan_proto = await self._asusrouter.connection.async_run_command(
                _ROUTER_WAN_PROTO_COMMAND)
            if wan_proto:
                if wan_proto[0] == 'dhcp' or wan_proto[0] == 'static':
                    self._rates = await self._asusrouter.async_get_bytes_total()
                    self._speed = await self._asusrouter.async_get_current_transfer_rates()
                else:
                    self._rates = await self.async_get_bytes_total()
                    self._speed = await self.async_get_current_transfer_rates()
                    await self.async_get_ppoe_vpn()

            wifi_states_5g = await self._asusrouter.connection.async_run_command(
                _STATES_WIFI_5G_CMD)
            if wifi_states_5g and wifi_states_5g[0].isdigit():
                self._5g_wifi = int(wifi_states_5g[0])

            wifi_states_2g = await self._asusrouter.connection.async_run_command(
                _STATES_WIFI_2G_CMD)
            if wifi_states_2g and wifi_states_2g[0].isdigit():
                self._2g_wifi = int(wifi_states_2g[0])

            self._5g_wl_channel = self.get_channel_from_line(await self._asusrouter.connection.async_run_command(
                _WIFI_CHANNEL_5G_CMD))

            self._2g_wl_channel = self.get_channel_from_line(await self._asusrouter.connection.async_run_command(
                _WIFI_CHANNEL_2G_CMD))

            if self._5g_wifi==1 or self._2g_wifi==1:
                await self._asusrouter.set_wifi_enabled(True)
            else:
                await self._asusrouter.set_wifi_enabled(False)

            await self.get_dhcp_clients()

            self._connected = True
            await self.async_get_public_ip()

            await self.pub_data_mqtt()

            await self._asusrouter.set_vpn_user(self._ppoe_username)
            await self._asusrouter.set_vpn_server(self._ppoe_heartbeat)

        except  Exception as e:
            self._connected = False
            await self._asusrouter.set_public_ip("0.0.0.0")
            if self._asusrouter.connect_failed:
                await self._asusrouter.set_device_state('0')
            _LOGGER.error(e)


class AsuswrtRouterSensor(AsuswrtSensor):
    """This is the interface class."""

    @property
    def name(self):
        """Return the name of the router."""
        return "asusrouter_%s" % (self._name)

    @property
    def wan_ip(self):
        """Return the wan ip of router."""
        return self._wan_ip

    @property
    def download(self):
        """Return the total download."""
        if self._rates:
            return round(self._rates[0]/1000000000, 2)
        return 0

    @property
    def upload(self):
        """Return the total upload."""
        if self._rates:
            return round(self._rates[1]/1000000000, 2)
        return 0

    @property
    def download_speed(self):
        """Return the download speed."""
        if self._speed:
            return round(self._speed[0]/1000, 2)
        return 0

    @property
    def upload_speed(self):
        """Return the upload speed."""
        if self._speed:
            return round(self._speed[1]/1000, 2)
        return 0
      
    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {
            'initialized': self._initialized,
            'wan_ip': self._wan_ip,
            'public_ip': self._asusrouter.public_ip,
            'download': self.download,
            'upload': self.upload,
            'download_speed': self.download_speed,
            'upload_speed': self.upload_speed,
            'connect_state': self._connected,
            'ssid': self._asusrouter.ssid,
            'host': self._asusrouter.host,
            'client_number': self._client_number,
            '2.4G_wifi': self._2g_wifi,
            '2.4G_wifi_channel': self._2g_wl_channel,
            '5G_wifi': self._5g_wifi,
            '5G_wifi_channel': self._5g_wl_channel,
            'vpn_username': self._ppoe_username,
            'vpn_server': self._ppoe_heartbeat,
            'vpn_proto': self._ppoe_proto,
        }

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._asusrouter.device_state


class RouterWanIpSensor(AsuswrtRouterSensor):
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

class RouterPublicIpSensor(AsuswrtRouterSensor):
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
        self._state = self._asusrouter.public_ip

class RouterHostSensor(AsuswrtRouterSensor):
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
        self._state = self._asusrouter.host

class RouterClientCountSensor(AsuswrtRouterSensor):
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
        self._state = self._client_number

class RouterInitStateSensor(AsuswrtRouterSensor):
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

class RouterDownloadSensor(AsuswrtRouterSensor):
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

class RouterUploadSensor(AsuswrtRouterSensor):
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

class RouterDownloadSpeedSensor(AsuswrtRouterSensor):
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
        self._state =  super().download_speed

class RouterUploadSpeedSensor(AsuswrtRouterSensor):
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
        self._state =  super().upload_speed

class RouterVpnUsernameSensor(AsuswrtRouterSensor):
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

class RouterVpnServerSensor(AsuswrtRouterSensor):
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

class RouterVpnProtoSensor(AsuswrtRouterSensor):
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