"""Sidebar panel for RESTOCK."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from aiohttp import web

from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, PANEL_URL_PATH
from .store import RestockInventory

_LOGGER = logging.getLogger(__name__)

PANEL_COMPONENT_NAME = "restock-panel"
PANEL_MODULE_URL = "/api/restock/panel.js"
PANEL_FRONTEND_PATH = Path(__file__).with_name("panel_frontend.js")


def async_register_panel(hass: HomeAssistant) -> None:
    """Register the RESTOCK sidebar panel, frontend module, and API views."""
    hass.http.register_view(RestockPanelModuleView())
    websocket_api.async_register_command(hass, websocket_overview)
    frontend.add_extra_js_url(hass, PANEL_MODULE_URL)
    frontend.async_register_built_in_panel(
        hass,
        component_name=PANEL_COMPONENT_NAME,
        sidebar_title="RESTOCK",
        sidebar_icon="mdi:package-variant-closed",
        frontend_url_path=PANEL_URL_PATH,
        config={"domain": DOMAIN},
        require_admin=False,
    )
    _LOGGER.info("Registered RESTOCK sidebar panel: path=%s", PANEL_URL_PATH)


def async_unregister_panel(hass: HomeAssistant) -> None:
    """Remove the RESTOCK sidebar panel."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    frontend.remove_extra_js_url(hass, PANEL_MODULE_URL)
    _LOGGER.info("Unregistered RESTOCK sidebar panel: path=%s", PANEL_URL_PATH)


class RestockPanelModuleView(HomeAssistantView):
    """Serve the RESTOCK panel frontend module."""

    url = PANEL_MODULE_URL
    name = "api:restock:panel:js"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Return the panel JavaScript module."""
        hass: HomeAssistant = request.app["hass"]
        content = await hass.async_add_executor_job(
            PANEL_FRONTEND_PATH.read_text,
            "utf-8",
        )
        return web.Response(
            text=content,
            content_type="text/javascript",
            headers={"Cache-Control": "no-store"},
        )


@callback
@websocket_api.websocket_command({vol.Required("type"): "restock/overview"})
def websocket_overview(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return RESTOCK overview data to the authenticated frontend."""
    manager = _manager(hass)
    data = _overview_data(manager)
    _LOGGER.debug(
        "Served RESTOCK overview data: containers=%d locations=%d logbook=%d",
        data["summary"]["containers"],
        data["summary"]["locations"],
        len(data["logbook"]),
    )
    connection.send_result(msg["id"], data)


def _manager(hass: HomeAssistant) -> RestockInventory:
    """Return the first loaded RESTOCK manager."""
    return next(iter(hass.data[DOMAIN].values()))


def _overview_data(manager: RestockInventory) -> dict[str, Any]:
    """Build practical overview data for the panel."""
    containers = sorted(
        manager.containers.values(),
        key=lambda container: container.get("updated_at") or "",
        reverse=True,
    )
    locations = [
        {
            "name": location["name"],
            "containers": manager.location_count(location_key),
        }
        for location_key, location in sorted(
            manager.locations.items(), key=lambda item: item[1]["name"].casefold()
        )
    ]
    total_quantity = sum(int(container.get("quantity", 0)) for container in containers)
    empty_containers = [
        _container_summary(container)
        for container in containers
        if int(container.get("quantity", 0)) == 0
    ]
    low_containers = [
        _container_summary(container)
        for container in containers
        if 0 < int(container.get("quantity", 0)) <= 2
    ]

    return {
        "summary": {
            "containers": len(containers),
            "locations": len(manager.locations),
            "total_quantity": total_quantity,
            "empty": len(empty_containers),
            "low": len(low_containers),
        },
        "containers": [_container_summary(container) for container in containers],
        "locations": locations,
        "empty_containers": empty_containers[:8],
        "low_containers": low_containers[:8],
        "logbook": list(reversed(manager.logbook[-50:])),
    }


def _container_summary(container: dict[str, Any]) -> dict[str, Any]:
    """Return display-safe container data."""
    return {
        "tag_id": container.get("tag_id"),
        "name": container.get("item_label") or container.get("name") or "Container",
        "format": container.get("item_format") or "",
        "quantity": int(container.get("quantity", 0)),
        "unit": container.get("unit") or "items",
        "location": container.get("location") or "Unassigned",
        "state": container.get("state") or "unknown",
        "updated_at": container.get("updated_at") or "",
        "created_at": container.get("created_at") or "",
    }
