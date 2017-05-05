"""
Support for monitoring a Smappee energy sensor.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.smappee/
"""
import logging
import math
from datetime import datetime, timedelta

#from homeassistant.components.smappee import DATA_SMAPPEE, DOMAIN
from custom_components.smappee import DATA_SMAPPEE, DOMAIN
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

SENSOR_PREFIX = 'Smappee'
SENSOR_TYPES = {
    'consumption': ['Consumption', 'mdi:power-plug'],
    'solar': ['Solar', 'mdi:white-balance-sunny'],
    'alwaysOn': ['Always On', 'mdi:gauge']
}

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=1)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Smappee sensor."""
    smappee = hass.data[DATA_SMAPPEE]

    dev = []
    for location_id, location_name in smappee.locations.items():
        for sensor in SENSOR_TYPES:
            dev.append(SmappeeSensor(smappee, location_id, sensor))

    add_devices(dev)


class SmappeeSensor(Entity):
    """Implementation of a Smappee sensor."""

    def __init__(self, smappee, location_id, sensor):
        """Initialize the sensor."""
        self._smappee = smappee
        self._location_id = location_id
        self._sensor = sensor
        self.data = None
        self._unit_of_measurement = 'W'
        self._state = None
        self._timestamp = None
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} {} {}".format(SENSOR_PREFIX,
                                 self._smappee.locations[self._location_id],
                                 SENSOR_TYPES[self._sensor][0])

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return SENSOR_TYPES[self._sensor][1]

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attr = {}
        attr['Location Id'] = self._location_id
        attr['Location Name'] = self._smappee.locations[self._location_id]
        attr['Last Update'] = datetime.fromtimestamp(self._timestamp/1000.0)
        return attr

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from Smappee and update the state."""
        data = self._smappee.get_consumption(self._location_id)
        consumption = data.get('consumptions')[-1]

        self._timestamp = consumption.get('timestamp')
        self._state = consumption.get(self._sensor)
