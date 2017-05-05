"""Playstation 4 media_player using ps4-waker."""
import json
import re
import subprocess
import logging
import urllib.request
from datetime import timedelta
from urllib.parse import urlparse

import voluptuous as vol

import homeassistant.util as util
from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MEDIA_TYPE_CHANNEL,
    SUPPORT_TURN_ON,
    SUPPORT_TURN_OFF,
    SUPPORT_STOP,
    SUPPORT_SELECT_SOURCE,
    MediaPlayerDevice
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_UNKNOWN,
    STATE_OFF,
    STATE_PLAYING,
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_FILENAME
)
from homeassistant.helpers import config_validation as cv

REQUIREMENTS = []

_LOGGER = logging.getLogger(__name__)

SUPPORT_PS4 = SUPPORT_TURN_OFF | SUPPORT_TURN_ON | \
    SUPPORT_STOP | SUPPORT_SELECT_SOURCE

DEFAULT_NAME = 'Playstation 4'
DEFAULT_PORT = ''
ICON = 'mdi:playstation'
CONF_GAMES_FILENAME = 'games_filename'

PS4WAKER_CONFIG_FILE = '.ps4-wake.credentials.json'
PS4_GAMES_FILE = 'ps4-games.json'
MEDIA_IMAGE_DEFAULT = None
MEDIA_IMAGE_SEARCH = 'https://kiot.nl/wp-admin/admin-ajax.php' + \
                     '?action=cfdb-export' + \
                     '&form=GameImages' + \
                     '&show=Game-ID%2Cimage-url' + \
                     '&role=Anyone' + \
                     '&enc=JSON' + \
                     '&search='

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
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
    port = config.get(CONF_PORT)
    credentials = hass.config.path(config.get(CONF_FILENAME))
    games_filename = hass.config.path(config.get(CONF_GAMES_FILENAME))

    ps4 = PS4Waker(host, port, credentials, games_filename)
    add_devices([PS4Device(name, ps4)], True)


class PS4Device(MediaPlayerDevice):
    """Representation of a PS4."""

    def __init__(self, name, ps4):
        """Initialize the ps4 device."""
        self.ps4 = ps4
        self._name = name
        self._state = STATE_UNKNOWN
        self._media_content_id = None
        self._media_title = None
        self._media_image_url = MEDIA_IMAGE_DEFAULT
        self._current_source = None
        self._current_source_id = None
        self.update()

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update(self):
        """Retrieve the latest data."""
        data = self.ps4.search()

        if self._media_content_id is not None and \
           self._media_content_id is not data.get('running-app-titleid'):
            _LOGGER.debug("titleid changed from %s to %s fetch new image",
                          self._media_content_id,
                          data.get('running-app-titleid'))
            self.update_image(data.get('running-app-titleid'))

        self._media_title = data.get('running-app-name')
        self._media_content_id = data.get('running-app-titleid')
        self._current_source = data.get('running-app-name')
        self._current_source_id = data.get('running-app-titleid')

        if data.get('status') == 'Ok':
            if self._media_content_id is not None:
                self._state = STATE_PLAYING
            else:
                self._state = STATE_IDLE
        else:
            self._state = STATE_OFF
            self._media_title = None
            self._media_content_id = None
            self._current_source = None
            self._current_source_id = None
            self._media_image_url = MEDIA_IMAGE_DEFAULT

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
    def media_image_url(self):
        """Image url of current playing media."""
        return self._media_image_url

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
        self.update()

    def media_pause(self):
        """Send keypress ps to return to menu."""
        self.ps4.remote('ps')
        self.update()

    def media_stop(self):
        """Send keypress ps to return to menu."""
        self.ps4.remote('ps')
        self.update()

    def select_source(self, source):
        """Select input source."""
        for titleid, game in self.ps4.games.items():
            if source == game:
                self.ps4.start(titleid)
                self.update_image(titleid)
                self._current_source_id = titleid
                self._current_source = game
                self._media_content_id = titleid
                self._media_title = game
                self.update()

    def update_image(self, titleid):
        """Update media_image from json lookup."""
        if titleid is None:
            self._media_image_url = MEDIA_IMAGE_DEFAULT
            return
        try:
            url = MEDIA_IMAGE_SEARCH + titleid
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req).read()
            search_result = json.loads(response.decode('utf-8'))
            if search_result:
                self._media_image_url = search_result[0]['image-url']
            if search_result == []:
                self._media_image_url = MEDIA_IMAGE_DEFAULT
        except urllib.error.URLError as e:
            _LOGGER.debug('Fetching image-url for %s failed %s',
                          titleid, e.reason)


class PS4Waker(object):
    """The class for handling the data retrieval."""

    def __init__(self, host, port, credentials, games_filename):
        """Initialize the data object."""
        self._host = host
        self._port = port
        self._credentials = credentials
        self._games_filename = games_filename
        self.games = {}
        self._load_games()

    def _run(self, command):
        """Get the latest data with a shell command."""
        bind_port = ''
        if self._port not in['']:
            bind_port = ' --bind-port ' + self._port

        cmd = 'ps4-waker -c ' + self._credentials + \
              ' -d ' + self._host + \
              ' -t 5000' + bind_port + \
              ' ' + \
              command
        _LOGGER.debug('Running: %s', cmd)

        try:
            return_value = subprocess.check_output(cmd, shell=True,
                                                   timeout=10,
                                                   stderr=subprocess.STDOUT)
            _LOGGER.debug('Return value: %s', return_value)
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
        """Wake PS4 up."""
        return self._run('')

    def search(self):
        """List current info."""
        value = self._run('search')

        if value is None:
            return {}

        if value.find("Could not detect any matching PS4 device") > -1:
            return {}

        """Get data between `{}`"""
        value = re.findall(r'{([^]]*)}', value)[0]
        value = '{%s}' % value

        try:
            data = json.loads(value)
        except json.decoder.JSONDecodeError as e:
            _LOGGER.error("Error decoding ps4 json : %s", e)
            data = {}

        """Save current game"""
        if data.get('running-app-titleid'):
            if data.get('running-app-titleid') not in self.games.keys():
                game = {data.get('running-app-titleid'):
                        data.get('running-app-name')}
                self.games.update(game)
                self._save_games()

        return data

    def standby(self):
        """Set PS4 into standby mode."""
        return self._run('standby')

    def start(self, titleId):
        """Start game using titleId."""
        return self._run('start ' + titleId)

    def remote(self, key):
        """Send remote key press."""
        return self._run('remote ' + key)
