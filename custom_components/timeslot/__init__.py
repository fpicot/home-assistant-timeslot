'''
Define a timeslot with 3 parameters : start, end, enabled
The state will return True if it is enabled and current time is between start and end, False in any other situation
'''

from __future__ import annotations

from datetime import (
    datetime,
    time as time_sys,
    timedelta
)

import logging
from typing import final
import voluptuous as vol

from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType

from homeassistant.const import (
    ATTR_EDITABLE,
    CONF_ID,
    CONF_NAME,
    CONF_UNIQUE_ID,
    STATE_ON,
    STATE_OFF,
    SERVICE_TOGGLE,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'timeslot'

ATTR_NAME = 'name'
ATTR_ENABLED = 'enabled'
ATTR_START = 'start'
ATTR_END = 'end'

ATTR_SCHEMA = {
    vol.Optional(ATTR_NAME): vol.All(str, vol.Length(min=1)),
    vol.Optional(ATTR_ENABLED): cv.boolean,
    vol.Optional(ATTR_START): cv.time,
    vol.Optional(ATTR_END): cv.time,
}

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: cv.schema_with_slug_keys(vol.Any(ATTR_SCHEMA,None))
},extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:

    entities = []
    for id_, conf in config.get(DOMAIN,{}).items():
        entities.append(Timeslot({CONF_ID: id_, **(conf or {})}))

    component = EntityComponent(_LOGGER, DOMAIN, hass)
    await component.async_add_entities(entities,False)


    component.async_register_entity_service(SERVICE_TURN_ON, {}, "async_turn_on")
    component.async_register_entity_service(SERVICE_TURN_OFF, {}, "async_turn_off")
    component.async_register_entity_service(SERVICE_TOGGLE, {}, "async_toggle")

    component.async_register_entity_service("set_parameters", cv.make_entity_service_schema(ATTR_SCHEMA), "async_set_parameters")

    return True



class Timeslot(ToggleEntity,RestoreEntity):
    """Representation of a timeslot."""

    def __init__(self, config: ConfigType) -> None:
        """Initialize a timeslot."""
        self._config = config
        self.editable = True
        self._attr_name: str = config.get(CONF_NAME)
        self._attr_unique_id: str = config.get(CONF_ID)
        self.entity_id = f"{DOMAIN}.{config.get(CONF_ID)}"

        self._enabled: bool = config.get(ATTR_ENABLED,False)
        self._start = config.get(ATTR_START,time_sys())
        self._end = config.get(ATTR_END,time_sys())

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def enabled(self) -> bool:
        """Return the status of the timeslot"""
        return self._enabled

    @property
    def start(self) -> time_sys:
        """Return the start time of the timeslot"""
        return self._start

    @property
    def end(self) -> time_sys:
        """Return the end time of the timeslot"""
        return self._end

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes."""
        attrs = {
            ATTR_EDITABLE: self.editable,
            ATTR_ENABLED: self._enabled,
            ATTR_START: self._start.isoformat() if self._start else None,
            ATTR_END: self._end.isoformat() if self._end else None
        }
        return attrs

    @property
    @final
    def state(self) -> str | None:
        """Return the state."""
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        now = datetime.now().time()
        if self._start <= self._end:
            return self._enabled and self._start <= now and now < self._end
        else:
            # Night timeslot
            return self._enabled and (self._start <= now or now < self._end)

    def turn_on(self, **kwargs: Any) -> None:
        """Enable the timestlot"""
        self._enabled = True

    def turn_off(self, **kwargs: Any) -> None:
        """Disable the timeslot"""
        self._enabled = False

    @callback
    def async_set_parameters(self, name: str | None = None, enabled: boolean | None = None, start: time_sys | None = None, end: time_sys | None = None) -> None:
        if name is not None:
            self._attr_name = name

        if enabled is not None:
           self._enabled = enabled

        if start is not None:
           self._start = start

        if end is not None:
           self._end = end

        self.async_write_ha_state()

    @callback
    def _async_update(self, now=None) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Restore object after restart, but don't override config
        old_state = await self.async_get_last_state()
        if old_state is not None:
            if self._config.get(ATTR_ENABLED) is None: self._enabled = old_state.attributes[ATTR_ENABLED]
            if self._config.get(ATTR_START) is None: self._start = time_sys.fromisoformat(old_state.attributes[ATTR_START])
            if self._config.get(ATTR_END) is None: self._end = time_sys.fromisoformat(old_state.attributes[ATTR_END])

        # Update state every minute
        async_track_time_interval(self.hass, self._async_update, timedelta(minutes=1))
