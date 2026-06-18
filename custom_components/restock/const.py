"""Constants for the RESTOCK integration."""

from __future__ import annotations

DOMAIN = "restock"
NAME = "RESTOCK"

PLATFORMS = ["sensor"]

CONF_INITIAL_LOCATIONS = "initial_locations"
CONF_M5DIAL_SERVICE_PREFIX = "m5dial_service_prefix"

DEFAULT_STATES = ["unknown", "frozen", "thawed", "room_temp", "empty"]
DEFAULT_UNIT = "items"
DEFAULT_M5DIAL_SERVICE_PREFIX = "m5dial_inventory"

MOCK_ITEMS = [
    {
        "id": "chicken_breast",
        "label": "Chicken breast",
        "format": "Vacuum pack",
        "unit": "pieces",
    },
    {
        "id": "beef_stew",
        "label": "Beef stew",
        "format": "1 L container",
        "unit": "servings",
    },
    {
        "id": "tomato_sauce",
        "label": "Tomato sauce",
        "format": "500 ml jar",
        "unit": "jars",
    },
    {
        "id": "berries",
        "label": "Mixed berries",
        "format": "Freezer bag",
        "unit": "cups",
    },
]

MOCK_LOCATIONS = ["Freezer", "Fridge", "Pantry", "Prep shelf"]

EVENT_INVENTORY_CONFIRM = "esphome.inventory_confirm"
EVENT_RESTOCK_SCAN = "esphome.restock_scan"
EVENT_RESTOCK_CREATE_CONTAINER = "esphome.restock_create_container"
EVENT_RESTOCK_UPDATE_CONTAINER = "esphome.restock_update_container"
EVENT_RESTOCK_UPDATED = "restock.updated"

SERVICE_CREATE_CONTAINER = "create_container"
SERVICE_CREATE_LOCATION = "create_location"
SERVICE_FILL_CONTAINER = "fill_container"
SERVICE_MOCK_API = "mock_api"
SERVICE_REMOVE_ITEMS = "remove_items"
SERVICE_SCAN_CONTAINER = "scan_container"
SERVICE_UPDATE_CONTAINER = "update_container"

SIGNAL_RESTOCK_ENTITY_ADDED = "restock_entity_added"

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
