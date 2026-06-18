"""Sensor platform for RESTOCK."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import slugify

from .const import DOMAIN, SIGNAL_RESTOCK_ENTITY_ADDED
from .store import RestockInventory


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RESTOCK sensors."""
    manager: RestockInventory = hass.data[DOMAIN][entry.entry_id]
    known_entities: set[str] = set()

    def build_container_entities(tag_id: str) -> list[SensorEntity]:
        return [
            RestockContainerQuantitySensor(manager, tag_id),
            RestockContainerTextSensor(manager, tag_id, "location"),
            RestockContainerTextSensor(manager, tag_id, "state"),
        ]

    def build_location_entities(location_key: str) -> list[SensorEntity]:
        return [RestockLocationSensor(manager, location_key)]

    @callback
    def add_entities(entities: list[RestockBaseSensor]) -> None:
        new_entities = [
            entity for entity in entities if entity.entity_key not in known_entities
        ]
        if not new_entities:
            return
        known_entities.update(entity.entity_key for entity in new_entities)
        async_add_entities(new_entities)

    add_entities(
        [
            entity
            for tag_id in manager.containers
            for entity in build_container_entities(tag_id)
        ]
    )
    add_entities(
        [
            entity
            for location_key in manager.locations
            for entity in build_location_entities(location_key)
        ]
    )

    @callback
    def handle_entity_added(kind: str, key: str) -> None:
        if kind == "container":
            add_entities(build_container_entities(key))
        elif kind == "location":
            add_entities(build_location_entities(key))

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_RESTOCK_ENTITY_ADDED, handle_entity_added
        )
    )


class RestockBaseSensor(SensorEntity):
    """Base class for RESTOCK sensors."""

    _attr_has_entity_name = True

    def __init__(self, manager: RestockInventory, entity_key: str) -> None:
        """Initialize the sensor."""
        self.manager = manager
        self.entity_key = entity_key
        self._unsub: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to inventory updates."""

        @callback
        def update() -> None:
            self.async_write_ha_state()

        self._unsub = self.manager.async_listen(update)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from inventory updates."""
        if self._unsub:
            self._unsub()
            self._unsub = None


class RestockContainerQuantitySensor(RestockBaseSensor):
    """Quantity sensor for a RESTOCK container."""

    _attr_icon = "mdi:counter"

    def __init__(self, manager: RestockInventory, tag_id: str) -> None:
        """Initialize the quantity sensor."""
        super().__init__(manager, f"container_{tag_id}_quantity")
        self.tag_id = tag_id
        self._attr_unique_id = f"{DOMAIN}_{slugify(tag_id)}_quantity"
        self._attr_translation_key = "container_quantity"

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return f"{self.container.get('name', self.tag_id)} quantity"

    @property
    def native_value(self) -> StateType:
        """Return the current quantity."""
        return self.container.get("quantity", 0)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the quantity unit."""
        return self.container.get("unit")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return self.container_attributes

    @property
    def container(self) -> dict[str, Any]:
        """Return this container."""
        return self.manager.containers.get(self.tag_id, {})

    @property
    def container_attributes(self) -> dict[str, Any]:
        """Return common container attributes."""
        container = self.container
        return {
            "tag_id": self.tag_id,
            "item_id": container.get("item_id"),
            "item_label": container.get("item_label"),
            "item_format": container.get("item_format"),
            "location": container.get("location"),
            "state": container.get("state"),
            "updated_at": container.get("updated_at"),
        }


class RestockContainerTextSensor(RestockBaseSensor):
    """Text-like sensor for a RESTOCK container property."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, manager: RestockInventory, tag_id: str, field: str) -> None:
        """Initialize the text sensor."""
        super().__init__(manager, f"container_{tag_id}_{field}")
        self.tag_id = tag_id
        self.field = field
        self._attr_icon = "mdi:map-marker" if field == "location" else "mdi:snowflake"
        self._attr_unique_id = f"{DOMAIN}_{slugify(tag_id)}_{field}"
        self._attr_translation_key = f"container_{field}"

    @property
    def name(self) -> str:
        """Return the sensor name."""
        return f"{self.container.get('name', self.tag_id)} {self.field}"

    @property
    def native_value(self) -> StateType:
        """Return the field value."""
        return self.container.get(self.field) or "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return {
            "tag_id": self.tag_id,
            "item_id": self.container.get("item_id"),
            "item_label": self.container.get("item_label"),
            "item_format": self.container.get("item_format"),
            "updated_at": self.container.get("updated_at"),
        }

    @property
    def container(self) -> dict[str, Any]:
        """Return this container."""
        return self.manager.containers.get(self.tag_id, {})


class RestockLocationSensor(RestockBaseSensor):
    """Sensor representing a RESTOCK location."""

    _attr_icon = "mdi:warehouse"
    _attr_translation_key = "location"

    def __init__(self, manager: RestockInventory, location_key: str) -> None:
        """Initialize the location sensor."""
        super().__init__(manager, f"location_{location_key}")
        self.location_key = location_key
        self._attr_unique_id = f"{DOMAIN}_location_{slugify(location_key)}"

    @property
    def name(self) -> str:
        """Return the location name."""
        return self.location.get("name", self.location_key)

    @property
    def native_value(self) -> StateType:
        """Return the number of containers in this location."""
        return self.manager.location_count(self.location_key)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit."""
        return "containers"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return {
            "location": self.location.get("name"),
            "created_at": self.location.get("created_at"),
        }

    @property
    def location(self) -> dict[str, Any]:
        """Return this location."""
        return self.manager.locations.get(self.location_key, {})
