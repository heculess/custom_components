"""Asusrouter status sensors."""
import logging
import math
from datetime import datetime
from homeassistant.helpers.entity import Entity
from . import AliddnsConfig
from . import DATA_ALIDDNS

import time
import hmac
from os import popen
from re import search
from json import loads
from re import compile
from sys import stdout
from hashlib import sha1
from requests import get
from requests import post
from random import randint
from urllib.request import urlopen
from urllib.request import Request
from urllib.parse import urlencode
from json import JSONDecoder
from urllib.error import HTTPError
from datetime import datetime
from urllib.parse import quote
from base64 import encodestring
import requests

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the asusrouter."""

    devices = []
    devices.append(AliddnsSensor(hass.data[DATA_ALIDDNS],hass))
    add_entities(devices, True)


class AliddnsSensor(Entity):
    """Representation of a asusrouter."""

    def __init__(self, aliddns_conf, hass):
        """Initialize the router."""
        self._name = aliddns_conf.name
        self._hass = hass
        self._state = None
        self.Aliyun_API_URL = "https://alidns.aliyuncs.com/?"
        self.access_id = aliddns_conf.access_id
        self.access_key = aliddns_conf.access_key
        self.domain = aliddns_conf.domain
        self.sub_domain = aliddns_conf.sub_domain
        self.Aliyun_API_Type = "A"
        self._record = None
        self._last_record = "0.0.0.0"
        self._update_time = ""

    @property
    def name(self):
        """Return the name of the ddns."""
        return self._name

    @property
    def state(self):
        """Return the state of the ddns."""
        return self._state

    @property  
    def device_state_attributes(self):
        """Return the state attributes."""	
        return {
            'update_time': self._update_time,
            'record': self._record,
            'domain': "%s.%s" % (self.sub_domain,self.domain),
            'last_record': self._last_record,
        }

    def AliyunSignature(self,parameters):
        sortedParameters = sorted(parameters.items(), key=lambda parameters: parameters[0])
        canonicalizedQueryString = ''
        for (k, v) in sortedParameters:
            canonicalizedQueryString += '&' + self.CharacterEncode(k) + '=' + self.CharacterEncode(v)
        stringToSign = 'GET&%2F&' + self.CharacterEncode(canonicalizedQueryString[1:])
        h = hmac.new((self.access_key + "&").encode('ASCII'), stringToSign.encode('ASCII'), sha1)
        signature = encodestring(h.digest()).strip()
        return signature

    def CharacterEncode(self,encodeStr):
        encodeStr = str(encodeStr)
        res = quote(encodeStr.encode('utf-8'), '')
        res = res.replace('+', '%20')
        res = res.replace('*', '%2A')
        res = res.replace('%7E', '~')
        return res

    def AliyunAPIPOST(self,Aliyun_API_Action):
        Aliyun_API_SD = {
            'Format': 'json',
            'Version': '2015-01-09',
            'AccessKeyId': self.access_id,
            'SignatureMethod': 'HMAC-SHA1',
            'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'SignatureVersion': '1.0',	
            'SignatureNonce': randint(0, 99999999999999),
            'Action': Aliyun_API_Action
        }
        return Aliyun_API_SD

    def check_record_id(self,sub_domain,domain):
        Aliyun_API_Post = self.AliyunAPIPOST('DescribeDomainRecords')
        Aliyun_API_Post['DomainName'] = domain
        Aliyun_API_Post['Signature'] = self.AliyunSignature(Aliyun_API_Post)
        Aliyun_API_Post = urlencode(Aliyun_API_Post)
        Aliyun_API_Request = get(self.Aliyun_API_URL + Aliyun_API_Post)

        domainRecords = ''
        try:
            domainRecords = Aliyun_API_Request.text
        except HTTPError as e:
            _LOGGER.error(e.code)

        try:
            result = JSONDecoder().decode(domainRecords)
            if not result:
                return -1
            result = result['DomainRecords']['Record']
            times = 0
            check = 0
            for record_info in result:
                if record_info['RR'] == sub_domain:
                    check = 1
                    break
                else:
                    times += 1
            if check:
                result = int(result[times]['RecordId'])
            else:
                result = -1
            return result
        except  Exception as e:
            _LOGGER.error(e)
            return -1

    def ip_from3322(self):
        try:
            ret = requests.get("http://members.3322.org/dyndns/getip")
        except requests.RequestException as ex:
            return None
        if ret.status_code != requests.codes.ok:
            return None
        return ret.content.decode('utf-8').rstrip("\n")

    def ip_from_sohu(self):
        get_ip_method = popen('curl -s https://pv.sohu.com/cityjson?ie=utf-8')
        if not get_ip_method:
            return None
        get_ip_responses = get_ip_method.readlines()[0]	
        if not get_ip_responses:
            return None
        get_ip_pattern = compile(r'(?<![\.\d])(?:\d{1,3}\.){3}\d{1,3}(?![\.\d])')	
        get_ip_value = get_ip_pattern.findall(get_ip_responses)
        if not get_ip_value:
            return None
        return get_ip_value[0]

    def ip_from_netcn(self):
        opener = urlopen('http://www.net.cn/static/customercare/yourip.asp')
        if not opener:
            return None
        strg = opener.read().decode('gbk')
        ipaddr = search('\d+\.\d+\.\d+\.\d+',strg).group(0)
        return ipaddr

    def get_ip(self):
        ip = self.ip_from3322()
        if ip:
            return ip
        ip = self.ip_from_sohu()
        if ip:
            return ip
        return self.ip_from_netcn()

    def old_ip(self,Aliyun_API_RecordID):
        Aliyun_API_Post = self.AliyunAPIPOST('DescribeDomainRecordInfo')
        Aliyun_API_Post['RecordId'] = Aliyun_API_RecordID
        Aliyun_API_Post['Signature'] = self.AliyunSignature(Aliyun_API_Post)
        Aliyun_API_Post = urlencode(Aliyun_API_Post)
        Aliyun_API_Request = get(self.Aliyun_API_URL + Aliyun_API_Post)
        result = JSONDecoder().decode(Aliyun_API_Request.text)
        return result['Value']

    def add_dns(self,domainIP):
        Aliyun_API_Post = self.AliyunAPIPOST('AddDomainRecord')
        Aliyun_API_Post['DomainName'] = self.domain
        Aliyun_API_Post['RR'] = self.sub_domain
        Aliyun_API_Post['Type'] = self.Aliyun_API_Type
        Aliyun_API_Post['Value'] = domainIP
        Aliyun_API_Post['Signature'] = self.AliyunSignature(Aliyun_API_Post)
        Aliyun_API_Post = urlencode(Aliyun_API_Post)
        Aliyun_API_Request = get(self.Aliyun_API_URL + Aliyun_API_Post)

    def delete_dns(self,Aliyun_API_RecordID):
        Aliyun_API_Post = self.AliyunAPIPOST('DeleteDomainRecord')
        Aliyun_API_Post['RecordId'] = Aliyun_API_RecordID
        Aliyun_API_Post['Signature'] = self.AliyunSignature(Aliyun_API_Post)
        Aliyun_API_Post = urlencode(Aliyun_API_Post)
        Aliyun_API_Request = get(self.Aliyun_API_URL + Aliyun_API_Post)

    def update_dns(self,Aliyun_API_RecordID, Aliyun_API_Value):
        Aliyun_API_Post = self.AliyunAPIPOST('UpdateDomainRecord')
        Aliyun_API_Post['RecordId'] = Aliyun_API_RecordID
        Aliyun_API_Post['RR'] = self.sub_domain
        Aliyun_API_Post['Type'] = self.Aliyun_API_Type
        Aliyun_API_Post['Value'] = Aliyun_API_Value
        Aliyun_API_Post['Signature'] = self.AliyunSignature(Aliyun_API_Post)
        Aliyun_API_Post = urlencode(Aliyun_API_Post)
        Aliyun_API_Request = get(self.Aliyun_API_URL + Aliyun_API_Post)

    def set_dns(self,Aliyun_API_RecordID, Aliyun_API_Enabled):
        Aliyun_API_Post = self.AliyunAPIPOST('SetDomainRecordStatus')
        Aliyun_API_Post['RecordId'] = Aliyun_API_RecordID
        Aliyun_API_Post['Status'] = "Enable" if Aliyun_API_Enabled else "Disable"
        Aliyun_API_Post['Signature'] = self.AliyunSignature(Aliyun_API_Post)
        Aliyun_API_Post = urlencode(Aliyun_API_Post)
        Aliyun_API_Request = get(self.Aliyun_API_URL + Aliyun_API_Post)

    async def async_update(self):
        """Fetch status from router."""
        try:
            rc_value = await self._hass.async_add_executor_job(self.get_ip)
            if not rc_value:
                rc_value = "0.0.0.0"

            rc_record_id = await self._hass.async_add_executor_job(self.check_record_id,
                self.sub_domain, self.domain)

            if rc_record_id < 0:
                await self._hass.async_add_executor_job(self.add_dns, rc_value)
                self._record = rc_value
                self._update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                
                rc_value_old = await self._hass.async_add_executor_job(self.old_ip, rc_record_id)
                self._record = rc_value
                if rc_value != rc_value_old:
                    self._last_record = rc_value_old
                    await self._hass.async_add_executor_job(self.update_dns, rc_record_id, rc_value)
                    self._update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._state = "on"
        except  Exception as e:
            _LOGGER.error(e)
            self._state = "error"
