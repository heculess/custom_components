"""Constants used by asusrouter."""

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

DOMAIN_MQTT_PUB = "router_mqtt_pub"
CONF_ROUTERS = "routers"

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

SET_INITED_FLAG_CMD = "touch /etc/inited ; service restart_firewall"

NETWORK_STATE_DOWNLOAD = "download"
NETWORK_STATE_UPLOAD = "upload"
NETWORK_STATE_DOWNLOAD_SPEED = "download_speed"
NETWORK_STATE_UPLOAD_SPEED = "upload_speed"

SECRET_GROUP = "Password or SSH Key"

