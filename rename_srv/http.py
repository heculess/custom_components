
from datetime import datetime, timedelta
import json
import logging
import traceback
import os
import re

from aiohttp import web
from aiohttp import hdrs

from homeassistant.util import dt as dt_util
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)

DOWNLOAD_FILE_NAME = {hdrs.CONTENT_DISPOSITION: f"fileName=zod_device.sh"}

class RenameGatewayView(HomeAssistantView):
    """View to handle Configuration requests."""

    url = '/zodShell'
    name = 'rename:group_device'

    requires_auth = False

    def __init__(self, hass):
        self._hass = hass
        self._states_run = False

    def set_state(self, is_run):
        self._states_run = is_run

    def get_state(self):
        return self._states_run

    async def get(self, request):
        """Update state of entity."""
        return await self.post(request)

    async def post(self, request):
        """Update state of entity."""
        try:
            start_time = datetime.now()
            _LOGGER.debug("[renamesrv_gateway] -------- start handle task from http at %s --------" % start_time.strftime('%Y-%m-%d %H:%M:%S'))
            data = request.query
            _LOGGER.debug("[renamesrv_gateway] raw message: %s", data)

            if self._states_run:
                return await self.handleRequest(data)
            else:
                response = {'status': 'service closed'}
        except:
            _LOGGER.error("[renamesrv_gateway] handle fail: %s", traceback.format_exc())
            response = {'error': traceback.format_exc()}
        finally:
            end_time = datetime.now()
            _LOGGER.debug("[renamesrv_gateway] -------- http task finish at %s, running time: %ss --------" % (end_time.strftime('%Y-%m-%d %H:%M:%S'), (end_time - start_time).total_seconds()))

        return self.json(response)


    async def handleRequest(self, data):
        """Handle request"""

        ssid = data.get("wifi")
        if not ssid:
            return self.json({'status': 'lost param'})
        cid = data.get("cid")
        gid = data.get("gid")
        oid = data.get("oid")
        _LOGGER.info("[renamesrv_gateway] Handle Request:\n%s" % data)

        group_dir = "/share/rename/%s" % ssid
        if not os.path.exists(group_dir):
            os.makedirs(group_dir)

        file_path = os.path.join(group_dir, cid)
        if not os.path.isfile(file_path):
            new_gid = self.get_gid(ssid)
            new_oid = self.get_oid(group_dir,ssid)

            if not new_gid:
                return self.json({'status': 'error ssid to make gid'})
            if not new_oid:
                return self.json({'status': 'error ssid to make oid'})

            with open(file_path, 'w') as record_file:
                content = "am force-stop zod.whale\nsetprop persist.zod.gid %s\n"\
                    "setprop persist.zod.oid %s\n"\
                    "am start -n zod.whale/.MainActivity" % (new_gid,new_oid)
                _LOGGER.info(content)
                record_file.write(content)
        
        _LOGGER.info("Respnose: %s", file_path)

        return web.FileResponse(file_path, headers=DOWNLOAD_FILE_NAME)

    def get_gid(self, ssid):

        try:
            group_head = re.sub("\d", "", ssid)
            group_id = int(re.sub("\D", "", ssid))
            if group_head == "KS":
                if group_id<1000:
                    group_id += 1000
                return "live%s" % group_id

            return None
        except:
            _LOGGER.error("error wifi param")

        return None
        
    def get_oid(self, folder, ssid):
        gid = self.get_gid(ssid)
        if not gid:
            return None
        return gid + '{:0>6d}'.format(self.get_file_count(folder)+1)

    def get_file_count(self, path):

        file_count = 0
        for lists in os.listdir(path):
            file_path = os.path.join(path, lists)
            if os.path.isfile(file_path):
                file_count += 1

        return file_count

class RenameGateway:
    def __init__(self, hass, name):
        self._hass = hass
        self._name = name
        self._gateway = RenameGatewayView(self._hass)

    def srv_start(self):
        self._gateway.set_state(True)

    def srv_stop(self):
        self._gateway.set_state(False)

    def srv_name(self):
        return self._name

    def is_running(self):
        return self._gateway.get_state()

    async def register_gateway(self):
        self._hass.http.register_view(self._gateway)

    