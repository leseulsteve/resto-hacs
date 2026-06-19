"""Storage and inventory model for RESTOCK."""

from __future__ import annotations

import logging

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .const import (
    CONF_INITIAL_LOCATIONS,
    DEFAULT_STATES,
    DEFAULT_UNIT,
    DOMAIN,
    EVENT_RESTOCK_UPDATED,
    MOCK_ITEMS,
    MOCK_LOCATIONS,
    SIGNAL_RESTOCK_ENTITY_ADDED,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def _utc_now() -> str:
    """Return an ISO-formatted UTC timestamp."""
    return datetime.now(UTC).isoformat()


class RestockInventory:
    """Manage RESTOCK inventory data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the inventory store."""
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self.data: dict[str, Any] = {"containers": {}, "locations": {}}
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        """Load inventory data from storage."""
        stored = await self._store.async_load()
        if stored:
            self.data = stored
            _LOGGER.debug(
                "Loaded RESTOCK storage: containers=%d locations=%d",
                len(self.containers),
                len(self.locations),
            )
        else:
            _LOGGER.debug("No RESTOCK storage found, starting with empty inventory")

        configured_locations = self.entry.options.get(
            CONF_INITIAL_LOCATIONS,
            self.entry.data.get(CONF_INITIAL_LOCATIONS, []),
        )
        known_locations = set(self.locations)
        for location in configured_locations:
            self.ensure_location(location, save=False)

        if set(self.locations) != known_locations:
            _LOGGER.debug(
                "Saving RESTOCK storage after seeding configured locations: locations=%d",
                len(self.locations),
            )
            await self.async_save(notify=False)

    @property
    def containers(self) -> dict[str, dict[str, Any]]:
        """Return all containers."""
        return self.data.setdefault("containers", {})

    @property
    def locations(self) -> dict[str, dict[str, Any]]:
        """Return all locations."""
        return self.data.setdefault("locations", {})

    def mock_api_payload(self) -> dict[str, Any]:
        """Return the current mock API payload."""
        configured_locations = [
            location["name"] for location in self.locations.values()
        ] or MOCK_LOCATIONS
        _LOGGER.debug(
            "Built RESTOCK mock API payload: items=%d locations=%d",
            len(MOCK_ITEMS),
            len(configured_locations),
        )
        return {"items": MOCK_ITEMS, "locations": configured_locations}

    def get_container(self, tag_id: str) -> dict[str, Any] | None:
        """Return a container by tag ID."""
        return self.containers.get(self._normalize_tag_id(tag_id))

    @callback
    def async_listen(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a listener for inventory changes."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            self._listeners.remove(listener)

        return unsubscribe

    def ensure_location(self, name: str | None, *, save: bool = False) -> str | None:
        """Ensure a location exists and return its canonical name."""
        if not name:
            return None

        name = str(name).strip()
        if not name:
            return None

        key = name.casefold()
        if key in self.locations:
            return self.locations[key]["name"]

        self.locations[key] = {"name": name, "created_at": _utc_now()}
        _LOGGER.info("Created RESTOCK location: name=%s", name)
        async_dispatcher_send(self.hass, SIGNAL_RESTOCK_ENTITY_ADDED, "location", key)
        if save:
            self.hass.async_create_task(self.async_save())
        return name

    async def async_create_location(self, name: str) -> None:
        """Create a location."""
        known_locations = set(self.locations)
        self.ensure_location(name)
        if set(self.locations) != known_locations:
            await self.async_save()

    async def async_create_container(
        self,
        *,
        tag_id: str,
        name: str | None = None,
        quantity: int = 0,
        location: str | None = None,
        state: str = "unknown",
        unit: str = DEFAULT_UNIT,
        item_id: str | None = None,
        item_label: str | None = None,
        item_format: str | None = None,
    ) -> None:
        """Create or replace a container."""
        tag_id = self._normalize_tag_id(tag_id)
        location = self._normalize_optional(location)
        if location:
            location = self.ensure_location(location)

        is_new = tag_id not in self.containers
        now = _utc_now()
        self.containers[tag_id] = {
            "tag_id": tag_id,
            "name": name or item_label or f"Container {tag_id}",
            "item_id": item_id,
            "item_label": item_label or name,
            "item_format": item_format,
            "quantity": max(0, int(quantity)),
            "location": location,
            "state": state or DEFAULT_STATES[0],
            "unit": unit or DEFAULT_UNIT,
            "created_at": self.containers.get(tag_id, {}).get("created_at", now),
            "updated_at": now,
        }
        if is_new:
            async_dispatcher_send(
                self.hass, SIGNAL_RESTOCK_ENTITY_ADDED, "container", tag_id
            )
        _LOGGER.info(
            "%s RESTOCK container: tag_id=%s name=%s quantity=%s location=%s state=%s",
            "Created" if is_new else "Replaced",
            tag_id,
            self.containers[tag_id].get("name"),
            self.containers[tag_id].get("quantity"),
            self.containers[tag_id].get("location"),
            self.containers[tag_id].get("state"),
        )
        await self.async_save()

    async def async_update_container(
        self,
        *,
        tag_id: str,
        quantity: int | None = None,
        delta: int | None = None,
        location: str | None = None,
        state: str | None = None,
        name: str | None = None,
        unit: str | None = None,
        item_id: str | None = None,
        item_label: str | None = None,
        item_format: str | None = None,
        create_missing: bool = False,
    ) -> None:
        """Update a container."""
        tag_id = self._normalize_tag_id(tag_id)
        if tag_id not in self.containers:
            if not create_missing:
                _LOGGER.debug(
                    "RESTOCK update rejected for unknown container: tag_id=%s",
                    tag_id,
                )
                raise KeyError(tag_id)
            _LOGGER.info(
                "Creating missing RESTOCK container during update: tag_id=%s",
                tag_id,
            )
            await self.async_create_container(tag_id=tag_id)

        container = self.containers[tag_id]
        before = dict(container)
        if quantity is not None:
            container["quantity"] = max(0, int(quantity))
        if delta is not None:
            container["quantity"] = max(0, int(container.get("quantity", 0)) + int(delta))
        if location is not None:
            location = self._normalize_optional(location)
            if location:
                location = self.ensure_location(location)
            container["location"] = location
        if state is not None:
            container["state"] = state
        if name is not None:
            container["name"] = name
        if unit is not None:
            container["unit"] = unit or DEFAULT_UNIT
        if item_id is not None:
            container["item_id"] = item_id
        if item_label is not None:
            container["item_label"] = item_label
            container["name"] = name or item_label
        if item_format is not None:
            container["item_format"] = item_format
        container["updated_at"] = _utc_now()
        _LOGGER.info(
            "Updated RESTOCK container: tag_id=%s quantity=%s->%s location=%s->%s state=%s->%s",
            tag_id,
            before.get("quantity"),
            container.get("quantity"),
            before.get("location"),
            container.get("location"),
            before.get("state"),
            container.get("state"),
        )
        await self.async_save()

    async def async_scan_container(
        self,
        *,
        tag_id: str,
        quantity: int | None = None,
        mode: str = "set",
    ) -> None:
        """Apply a scanner action to a container."""
        delta: int | None = None
        set_quantity: int | None = None

        if quantity is not None:
            if mode == "add":
                delta = int(quantity)
            elif mode == "remove":
                delta = -int(quantity)
            else:
                set_quantity = int(quantity)

        _LOGGER.debug(
            "Applying RESTOCK scan: tag_id=%s quantity=%s mode=%s set_quantity=%s delta=%s",
            tag_id,
            quantity,
            mode,
            set_quantity,
            delta,
        )
        await self.async_update_container(
            tag_id=tag_id,
            quantity=set_quantity,
            delta=delta,
            create_missing=True,
        )

    async def async_save(self, *, notify: bool = True) -> None:
        """Save inventory data and notify entities."""
        await self._store.async_save(self.data)
        _LOGGER.debug(
            "Saved RESTOCK storage: containers=%d locations=%d notify=%s",
            len(self.containers),
            len(self.locations),
            notify,
        )
        if notify:
            for listener in list(self._listeners):
                listener()
            self.hass.bus.async_fire(EVENT_RESTOCK_UPDATED, {})

    def location_count(self, location_key: str) -> int:
        """Return the number of containers assigned to a location."""
        location = self.locations.get(location_key)
        if not location:
            return 0
        location_name = location["name"]
        return sum(
            1
            for container in self.containers.values()
            if container.get("location") == location_name
        )

    @staticmethod
    def _normalize_tag_id(tag_id: str) -> str:
        """Normalize a tag ID."""
        tag_id = str(tag_id).strip()
        if not tag_id:
            raise ValueError("tag_id is required")
        return tag_id

    @staticmethod
    def _normalize_optional(value: str | None) -> str | None:
        """Normalize an optional text value."""
        if value is None:
            return None
        value = str(value).strip()
        return value or None
