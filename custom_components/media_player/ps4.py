"""
Playstation 4 media_player using ps4-waker
"""
import json
import re
import subprocess
import logging
import os
from datetime import timedelta
from urllib.parse import urlparse

import voluptuous as vol

import homeassistant.util as util
from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_CONTENT_ID,
    MEDIA_TYPE_CHANNEL,
    SUPPORT_TURN_ON,
    SUPPORT_TURN_OFF,
    SUPPORT_STOP,
    SUPPORT_SELECT_SOURCE,
    MediaPlayerDevice
)
from homeassistant.const import (
    DEVICE_DEFAULT_NAME,
    STATE_IDLE,
    STATE_UNKNOWN,
    STATE_OFF,
    STATE_PLAYING,
    CONF_NAME,
    CONF_HOST,
    CONF_FILENAME
)
from homeassistant.loader import get_component
from homeassistant.helpers import config_validation as cv

REQUIREMENTS = []

_LOGGER = logging.getLogger(__name__)

SUPPORT_PS4 = SUPPORT_TURN_OFF | SUPPORT_TURN_ON | \
    SUPPORT_STOP | SUPPORT_SELECT_SOURCE

DEFAULT_NAME = 'Playstation 4'
ICON = 'mdi:playstation'
CONF_GAMES_FILENAME = 'games_filename'

PS4WAKER_CONFIG_FILE = '.ps4-wake.credentials.json'
PS4_GAMES_FILE = 'ps4-games.json'

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_FILENAME, default=PS4WAKER_CONFIG_FILE): cv.string,
    vol.Optional(CONF_GAMES_FILENAME, default=PS4_GAMES_FILE): cv.string
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup PS4 platform."""
    if discovery_info is not None:
        host = urlparse(discovery_info[1]).hostname
    else:
        host = config.get(CONF_HOST)

    if host is None:
        _LOGGER.error("No PS4 found in configuration file or with discovery")
        return False

    name = config.get(CONF_NAME)
    credentials = hass.config.path(config.get(CONF_FILENAME))
    games_filename = hass.config.path(config.get(CONF_GAMES_FILENAME))

    ps4 = PS4Waker(host, credentials, games_filename)
    add_devices([PS4Device(name, ps4)], True)

class PS4Device(MediaPlayerDevice):
    """Representation of a PS4"""

    def __init__(self, name, ps4):
        """Initialize the ps4 device."""
        self.ps4 = ps4
        self._name = name
        self._state = STATE_UNKNOWN
        self._media_content_id = None
        self._media_title = None
        self._current_source = None
        self._current_source_id = None

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update(self):
        """Retrieve the latest data."""

        data = self.ps4.search()

        self._media_title = data.get('running-app-name')
        self._media_content_id = data.get('running-app-titleid')
        self._current_source = data.get('running-app-name')
        self._current_source_id = data.get('running-app-titleid')

        if data.get('status') == 'Ok':
            if self._media_content_id is not None:
                self._state = STATE_PLAYING
            else:
                self._state = STATE_IDLE
        elif data.get('status') == 'Standby':
            self._state = STATE_OFF
            self._current_source = None
            self._current_source_id = None
        else:
            self._state = STATE_OFF

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Icon."""
        return ICON

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        return self._media_content_id

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_CHANNEL

    @property
    def media_title(self):
        """Title of current playing media."""
        return self._media_title

    @property
    def supported_features(self):
        """Media player features that are supported."""
        return SUPPORT_PS4

    @property
    def source(self):
        """Return the current input source."""
        return self._current_source

    @property
    def source_list(self):
        """List of available input sources."""
        return sorted(self.ps4.games.values())


    def turn_off(self):
        """Turn off media player."""
        self.ps4.standby()

    def turn_on(self):
        """Turn on the media player."""
        self.ps4.wake()

    def media_pause(self):
        """stop media"""
        self.ps4.remote('ps')

    def media_stop(self):
        """stop media"""
        self.ps4.remote('ps')

    def select_source(self, source):
        """Select input source."""
        for titleid, game in self.ps4.games.items():
            if source == game:
                self.ps4.start(titleid)
                self._current_source_id = titleid
                self._current_source = game
                self._media_content_id = titleid
                self._media_title = game


class PS4Waker(object):
    """The class for handling the data retrieval."""

    def __init__(self, host, credentials, games_filename):
        """Initialize the data object."""
        self._host = host
        self._credentials = credentials
        self._games_filename = games_filename
        self.games = {}
        self._load_games()

    def _run(self, command):
        """Get the latest data with a shell command."""
        cmd = 'ps4-waker -c ' + self._credentials + \
              ' -d ' + self._host + \
              ' -t 5000 ' + \
              command
        _LOGGER.debug('Running: %s', cmd)

        try:
           return_value = subprocess.check_output(cmd, shell=True,
                                                  timeout=10, stderr=subprocess.STDOUT)
           return return_value.strip().decode('utf-8')
        except subprocess.CalledProcessError:
           _LOGGER.error('Command failed: %s', cmd)
        except subprocess.TimeoutExpired:
           _LOGGER.error('Timeout for command: %s', cmd)

        return None

    def _load_games(self):
        try:
            with open(self._games_filename, 'r') as f:
                self.games = json.load(f)
                f.close()
        except FileNotFoundError:
            self._save_games()

    def _save_games(self):
        try:
            with open(self._games_filename, 'w') as f:
                json.dump(self.games, f)
                f.close()
        except FileNotFoundError:
            pass

    def wake(self):
        return self._run('')

    def search(self):
        value = self._run('search')

        if value is None:
            return {}

        """Cleaning broken json"""
        value = re.sub(r"\"type\"", r'"pstype"', value)
        value = re.sub(r"{? *'(.+)': ([^,]*)", r'  \1: \2', value)
        value = re.sub(r"{? *(.+): ([^,]*)", r'"\1": \2', value)
        value = re.sub(r"'(.*)'", r'"\1"', value)
        value = "{ " + value

        try:
            data = json.loads(value)
        except json.decoder.JSONDecodeError:
            data = {}

        """Save current game"""
        if data.get('running-app-titleid'):
            if data.get('running-app-titleid') not in self.games.keys():
                game = {data.get('running-app-titleid'): data.get('running-app-name')}
                self.games.update(game)
                self._save_games()

        return data

    def standby(self):
        return self._run('standby')

    def start(self, titleId):
        return self._run('start ' + titleId)

    def remote(self, key):
        return self._run('remote ' + key)
