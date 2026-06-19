"""The RESTOCK integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_M5DIAL_SERVICE_PREFIX,
    DEFAULT_STATES,
    DEFAULT_UNIT,
    DEFAULT_M5DIAL_SERVICE_PREFIX,
    DOMAIN,
    EVENT_RESTOCK_CREATE_CONTAINER,
    EVENT_RESTOCK_SCAN,
    EVENT_RESTOCK_UPDATE_CONTAINER,
    EVENT_INVENTORY_CONFIRM,
    MOCK_ITEMS,
    PLATFORMS,
    SERVICE_CREATE_CONTAINER,
    SERVICE_CREATE_LOCATION,
    SERVICE_FILL_CONTAINER,
    SERVICE_MOCK_API,
    SERVICE_REMOVE_ITEMS,
    SERVICE_SCAN_CONTAINER,
    SERVICE_UPDATE_CONTAINER,
)
from .panel import async_register_panel, async_unregister_panel
from .store import RestockInventory

_LOGGER = logging.getLogger(__name__)

ATTR_DELTA = "delta"
ATTR_LOCATION = "location"
ATTR_MODE = "mode"
ATTR_NAME = "name"
ATTR_QUANTITY = "quantity"
ATTR_STATE = "state"
ATTR_TAG_ID = "tag_id"
ATTR_UNIT = "unit"
ATTR_ITEM_FORMAT = "item_format"
ATTR_ITEM_ID = "item_id"
ATTR_ITEM_LABEL = "item_label"

SCAN_MODES = ["set", "add", "remove"]


def _positive_int(value) -> int:
    """Validate a positive integer."""
    value = cv.positive_int(value)
    if value < 1:
        raise vol.Invalid("value must be at least 1")
    return value


def _manager(hass: HomeAssistant) -> RestockInventory:
    """Return the loaded RESTOCK inventory manager."""
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data:
        raise ServiceValidationError("RESTOCK is not loaded")
    return next(iter(domain_data.values()))


def _mock_item(item_id: str | None) -> dict | None:
    """Return a mock API item by ID."""
    if not item_id:
        return None
    for item in MOCK_ITEMS:
        if item["id"] == item_id:
            return item
    return None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up RESTOCK services."""

    async def handle_create_location(call: ServiceCall) -> None:
        manager = _manager(hass)
        _LOGGER.info("Creating RESTOCK location: %s", call.data[ATTR_NAME])
        await manager.async_create_location(call.data[ATTR_NAME])

    async def handle_create_container(call: ServiceCall) -> None:
        manager = _manager(hass)
        item = _mock_item(call.data.get(ATTR_ITEM_ID))
        _LOGGER.info(
            "Creating RESTOCK container from service: tag_id=%s item_id=%s quantity=%s location=%s",
            call.data[ATTR_TAG_ID],
            call.data.get(ATTR_ITEM_ID),
            call.data.get(ATTR_QUANTITY, 0),
            call.data.get(ATTR_LOCATION),
        )
        await manager.async_create_container(
            tag_id=call.data[ATTR_TAG_ID],
            name=call.data.get(ATTR_NAME),
            quantity=call.data.get(ATTR_QUANTITY, 0),
            location=call.data.get(ATTR_LOCATION),
            state=call.data.get(ATTR_STATE, DEFAULT_STATES[0]),
            unit=call.data.get(ATTR_UNIT) or (item or {}).get("unit", DEFAULT_UNIT),
            item_id=call.data.get(ATTR_ITEM_ID),
            item_label=call.data.get(ATTR_ITEM_LABEL) or (item or {}).get("label"),
            item_format=call.data.get(ATTR_ITEM_FORMAT) or (item or {}).get("format"),
        )

    async def handle_update_container(call: ServiceCall) -> None:
        manager = _manager(hass)
        _LOGGER.info(
            "Updating RESTOCK container from service: tag_id=%s quantity=%s delta=%s location=%s state=%s",
            call.data[ATTR_TAG_ID],
            call.data.get(ATTR_QUANTITY),
            call.data.get(ATTR_DELTA),
            call.data.get(ATTR_LOCATION),
            call.data.get(ATTR_STATE),
        )
        try:
            await manager.async_update_container(
                tag_id=call.data[ATTR_TAG_ID],
                quantity=call.data.get(ATTR_QUANTITY),
                delta=call.data.get(ATTR_DELTA),
                location=call.data.get(ATTR_LOCATION),
                state=call.data.get(ATTR_STATE),
                name=call.data.get(ATTR_NAME),
                unit=call.data.get(ATTR_UNIT),
                item_id=call.data.get(ATTR_ITEM_ID),
                item_label=call.data.get(ATTR_ITEM_LABEL),
                item_format=call.data.get(ATTR_ITEM_FORMAT),
            )
        except KeyError as err:
            raise ServiceValidationError(
                f"Unknown RESTOCK container tag_id: {err.args[0]}"
            ) from err

    async def handle_fill_container(call: ServiceCall) -> None:
        manager = _manager(hass)
        _LOGGER.info(
            "Filling RESTOCK container: tag_id=%s quantity=%s",
            call.data[ATTR_TAG_ID],
            call.data[ATTR_QUANTITY],
        )
        try:
            await manager.async_update_container(
                tag_id=call.data[ATTR_TAG_ID],
                delta=call.data[ATTR_QUANTITY],
            )
        except KeyError as err:
            raise ServiceValidationError(
                f"Unknown RESTOCK container tag_id: {err.args[0]}"
            ) from err

    async def handle_remove_items(call: ServiceCall) -> None:
        manager = _manager(hass)
        _LOGGER.info(
            "Removing RESTOCK items: tag_id=%s quantity=%s",
            call.data[ATTR_TAG_ID],
            call.data[ATTR_QUANTITY],
        )
        try:
            await manager.async_update_container(
                tag_id=call.data[ATTR_TAG_ID],
                delta=-call.data[ATTR_QUANTITY],
            )
        except KeyError as err:
            raise ServiceValidationError(
                f"Unknown RESTOCK container tag_id: {err.args[0]}"
            ) from err

    async def handle_scan_container(call: ServiceCall) -> None:
        manager = _manager(hass)
        _LOGGER.info(
            "Applying RESTOCK scan service: tag_id=%s quantity=%s mode=%s",
            call.data[ATTR_TAG_ID],
            call.data.get(ATTR_QUANTITY),
            call.data.get(ATTR_MODE, "set"),
        )
        await manager.async_scan_container(
            tag_id=call.data[ATTR_TAG_ID],
            quantity=call.data.get(ATTR_QUANTITY),
            mode=call.data.get(ATTR_MODE, "set"),
        )

    async def handle_mock_api(call: ServiceCall) -> None:
        manager = _manager(hass)
        _LOGGER.debug("Firing RESTOCK mock API response event")
        hass.bus.async_fire("restock.mock_api_response", manager.mock_api_payload())

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_LOCATION,
        handle_create_location,
        schema=vol.Schema({vol.Required(ATTR_NAME): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_CONTAINER,
        handle_create_container,
        schema=vol.Schema(
            {
                vol.Required(ATTR_TAG_ID): cv.string,
                vol.Optional(ATTR_NAME): cv.string,
                vol.Optional(ATTR_QUANTITY, default=0): cv.positive_int,
                vol.Optional(ATTR_LOCATION): cv.string,
                vol.Optional(ATTR_STATE, default=DEFAULT_STATES[0]): cv.string,
                vol.Optional(ATTR_UNIT, default=DEFAULT_UNIT): cv.string,
                vol.Optional(ATTR_ITEM_ID): cv.string,
                vol.Optional(ATTR_ITEM_LABEL): cv.string,
                vol.Optional(ATTR_ITEM_FORMAT): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_CONTAINER,
        handle_update_container,
        schema=vol.Schema(
            {
                vol.Required(ATTR_TAG_ID): cv.string,
                vol.Optional(ATTR_NAME): cv.string,
                vol.Optional(ATTR_QUANTITY): cv.positive_int,
                vol.Optional(ATTR_DELTA): vol.Coerce(int),
                vol.Optional(ATTR_LOCATION): cv.string,
                vol.Optional(ATTR_STATE): cv.string,
                vol.Optional(ATTR_UNIT): cv.string,
                vol.Optional(ATTR_ITEM_ID): cv.string,
                vol.Optional(ATTR_ITEM_LABEL): cv.string,
                vol.Optional(ATTR_ITEM_FORMAT): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_FILL_CONTAINER,
        handle_fill_container,
        schema=vol.Schema(
            {
                vol.Required(ATTR_TAG_ID): cv.string,
                vol.Required(ATTR_QUANTITY): _positive_int,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_ITEMS,
        handle_remove_items,
        schema=vol.Schema(
            {
                vol.Required(ATTR_TAG_ID): cv.string,
                vol.Required(ATTR_QUANTITY): _positive_int,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SCAN_CONTAINER,
        handle_scan_container,
        schema=vol.Schema(
            {
                vol.Required(ATTR_TAG_ID): cv.string,
                vol.Optional(ATTR_QUANTITY): cv.positive_int,
                vol.Optional(ATTR_MODE, default="set"): vol.In(SCAN_MODES),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_MOCK_API,
        handle_mock_api,
        schema=vol.Schema({}),
    )
    _LOGGER.debug("Registered RESTOCK services")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RESTOCK from a config entry."""
    manager = RestockInventory(hass, entry)
    await manager.async_load()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    async_register_panel(hass)
    _LOGGER.info(
        "RESTOCK entry loaded: entry_id=%s containers=%d locations=%d",
        entry.entry_id,
        len(manager.containers),
        len(manager.locations),
    )

    async def call_m5dial(action: str, data: dict) -> None:
        """Call a user-defined ESPHome action on the M5Dial."""
        service_prefix = entry.options.get(
            CONF_M5DIAL_SERVICE_PREFIX,
            entry.data.get(CONF_M5DIAL_SERVICE_PREFIX, DEFAULT_M5DIAL_SERVICE_PREFIX),
        )
        service = f"{service_prefix}_{action}"
        _LOGGER.debug(
            "Calling ESPHome action esphome.%s with keys=%s",
            service,
            sorted(data),
        )
        try:
            await hass.services.async_call(
                "esphome",
                service,
                data,
                blocking=False,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Could not call ESPHome action esphome.%s: %s", service, err)

    async def show_create_flow(tag_id: str) -> None:
        """Tell the M5Dial to show the create-container flow."""
        payload = manager.mock_api_payload()
        _LOGGER.info(
            "Showing RESTOCK create flow on M5Dial: tag_id=%s items=%d locations=%d",
            tag_id,
            len(payload["items"]),
            len(payload["locations"]),
        )
        await call_m5dial(
            "show_create_container",
            {
                "tag_id": tag_id,
                "item_ids": [item["id"] for item in payload["items"]],
                "item_labels": [item["label"] for item in payload["items"]],
                "item_formats": [item["format"] for item in payload["items"]],
                "item_units": [item["unit"] for item in payload["items"]],
                "incoming_locations": payload["locations"],
            },
        )

    async def show_known_flow(tag_id: str, container: dict) -> None:
        """Tell the M5Dial to show the known-container flow."""
        payload = manager.mock_api_payload()
        _LOGGER.info(
            "Showing RESTOCK known flow on M5Dial: tag_id=%s quantity=%s location=%s",
            tag_id,
            container.get("quantity"),
            container.get("location"),
        )
        await call_m5dial(
            "show_known_container",
            {
                "tag_id": tag_id,
                "item_label": container.get("item_label")
                or container.get("name")
                or "Container",
                "item_format": container.get("item_format") or "",
                "quantity": int(container.get("quantity", 0)),
                "unit": container.get("unit") or DEFAULT_UNIT,
                "location": container.get("location") or "unknown",
                "state": container.get("state") or "unknown",
                "incoming_locations": payload["locations"],
            },
        )

    @callback
    def handle_restock_scan(event) -> None:
        """Handle a raw NFC scan from the M5Dial."""
        tag_id = event.data.get(ATTR_TAG_ID)
        if not tag_id:
            _LOGGER.debug("Ignoring RESTOCK scan event without tag_id")
            return
        container = manager.get_container(tag_id)
        if container:
            _LOGGER.info("Known RESTOCK NFC tag scanned: tag_id=%s", tag_id)
            hass.async_create_task(show_known_flow(tag_id, container))
        else:
            _LOGGER.info("Unknown RESTOCK NFC tag scanned: tag_id=%s", tag_id)
            hass.async_create_task(show_create_flow(tag_id))

    @callback
    def handle_create_from_dial(event) -> None:
        """Create a container from the M5Dial flow."""
        tag_id = event.data.get(ATTR_TAG_ID)
        if not tag_id:
            _LOGGER.debug("Ignoring RESTOCK create event without tag_id")
            return
        item = _mock_item(event.data.get(ATTR_ITEM_ID))
        quantity = event.data.get(ATTR_QUANTITY, 0)
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            _LOGGER.debug(
                "Invalid RESTOCK create quantity from M5Dial: tag_id=%s quantity=%s",
                tag_id,
                event.data.get(ATTR_QUANTITY),
            )
            quantity = 0
        _LOGGER.info(
            "Creating RESTOCK container from M5Dial: tag_id=%s item_id=%s quantity=%d location=%s",
            tag_id,
            event.data.get(ATTR_ITEM_ID),
            quantity,
            event.data.get(ATTR_LOCATION),
        )
        hass.async_create_task(
            manager.async_create_container(
                tag_id=tag_id,
                quantity=quantity,
                location=event.data.get(ATTR_LOCATION),
                state=event.data.get(ATTR_STATE, "unknown"),
                unit=event.data.get(ATTR_UNIT) or (item or {}).get("unit", DEFAULT_UNIT),
                item_id=event.data.get(ATTR_ITEM_ID),
                item_label=event.data.get(ATTR_ITEM_LABEL) or (item or {}).get("label"),
                item_format=event.data.get(ATTR_ITEM_FORMAT)
                or (item or {}).get("format"),
            )
        )

    @callback
    def handle_update_from_dial(event) -> None:
        """Update a container from the M5Dial flow."""
        tag_id = event.data.get(ATTR_TAG_ID)
        if not tag_id:
            _LOGGER.debug("Ignoring RESTOCK update event without tag_id")
            return
        quantity = event.data.get(ATTR_QUANTITY)
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            _LOGGER.debug(
                "Ignoring RESTOCK update with invalid quantity: tag_id=%s quantity=%s",
                tag_id,
                quantity,
            )
            return
        _LOGGER.info(
            "Updating RESTOCK container from M5Dial: tag_id=%s quantity=%d location=%s",
            tag_id,
            quantity,
            event.data.get(ATTR_LOCATION),
        )
        hass.async_create_task(
            manager.async_update_container(
                tag_id=tag_id,
                quantity=quantity,
                location=event.data.get(ATTR_LOCATION),
                create_missing=True,
            )
        )

    @callback
    def handle_inventory_confirm(event) -> None:
        """Handle scanner events from ESPHome/M5Dial."""
        tag_id = event.data.get(ATTR_TAG_ID)
        if not tag_id:
            _LOGGER.debug("Ignoring RESTOCK inventory confirm event without tag_id")
            return
        quantity = event.data.get(ATTR_QUANTITY)
        if quantity is not None:
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                _LOGGER.debug(
                    "Ignoring RESTOCK inventory confirm with invalid quantity: tag_id=%s quantity=%s",
                    tag_id,
                    quantity,
                )
                return
        mode = event.data.get(ATTR_MODE, "set")
        _LOGGER.info(
            "Applying RESTOCK inventory confirm event: tag_id=%s quantity=%s mode=%s",
            tag_id,
            quantity,
            mode,
        )
        hass.async_create_task(
            manager.async_scan_container(tag_id=tag_id, quantity=quantity, mode=mode)
        )

    entry.async_on_unload(
        hass.bus.async_listen(EVENT_INVENTORY_CONFIRM, handle_inventory_confirm)
    )
    entry.async_on_unload(hass.bus.async_listen(EVENT_RESTOCK_SCAN, handle_restock_scan))
    entry.async_on_unload(
        hass.bus.async_listen(EVENT_RESTOCK_CREATE_CONTAINER, handle_create_from_dial)
    )
    entry.async_on_unload(
        hass.bus.async_listen(EVENT_RESTOCK_UPDATE_CONTAINER, handle_update_from_dial)
    )
    _LOGGER.debug("Registered RESTOCK event listeners")
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload RESTOCK when options change."""
    _LOGGER.info("Reloading RESTOCK entry after options update: %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a RESTOCK config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            async_unregister_panel(hass)
        _LOGGER.info("RESTOCK entry unloaded: entry_id=%s", entry.entry_id)
    return unload_ok
