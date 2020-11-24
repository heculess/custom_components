"""Module for connections."""
import asyncio
import logging
from asyncio import LimitOverrunError, TimeoutError

import asyncssh

_LOGGER = logging.getLogger(__name__)

_PATH_EXPORT_COMMAND = "PATH=$PATH:/bin:/usr/sbin:/sbin"
asyncssh.set_log_level('WARNING')


class SshConnection:
    """Maintains an SSH connection to an router."""

    def __init__(self, host, port, username, password, ssh_key):
        """Initialize the SSH connection properties."""

        self._connected = False
        self._host = host
        self._port = port or 22
        self._username = username
        self._password = password
        self._ssh_key = ssh_key
        self._client = None
        self.last_error = None

    async def async_run_command(self, command, retry=False):
        """Run commands through an SSH connection.

        Connect to the SSH server if not currently connected, otherwise
        use the existing connection.
        """
        self._last_error = None

        if not self.is_connected:
            await self.async_connect()
        try:
            result = await asyncio.wait_for(self._client.run(
                "%s && %s" % (_PATH_EXPORT_COMMAND, command)), 9)
        except asyncssh.misc.ChannelOpenError:
            if not retry:
                await self.async_connect()
                return self.async_run_command(command, retry=True)
            else:
                self._connected = False
                _LOGGER.error("No connection to host")
                return []
        except TimeoutError:
            del self._client
            self._connected = False
            _LOGGER.error("Host timeout.")
            return []

        self._connected = True
        self.last_error = result.stderr
        return result.stdout.split('\n')

    @property
    def is_connected(self):
        """Do we have a connection."""
        return self._connected

    async def async_connect(self):
        """Fetches the client or creates a new one."""

        kwargs = {
            'username': self._username if self._username else None,
            'client_keys': [self._ssh_key] if self._ssh_key else None,
            'port': self._port,
            'password': self._password if self._password else None,
            'known_hosts': None
        }

        self._client = await asyncssh.connect(self._host, **kwargs)
        self._connected = True