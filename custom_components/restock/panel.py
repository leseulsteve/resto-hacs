"""Sidebar panel for RESTOCK."""

from __future__ import annotations

import logging

from typing import Any

from aiohttp import web

from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_URL_PATH
from .store import RestockInventory

_LOGGER = logging.getLogger(__name__)


def async_register_panel(hass: HomeAssistant) -> None:
    """Register the RESTOCK sidebar panel and API views."""
    hass.http.register_view(RestockOverviewView())
    hass.http.register_view(RestockOverviewDataView())
    frontend.async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title="RESTOCK",
        sidebar_icon="mdi:package-variant-closed",
        frontend_url_path=PANEL_URL_PATH,
        config={"url": "/api/restock/overview"},
        require_admin=False,
    )
    _LOGGER.info("Registered RESTOCK sidebar panel: path=%s", PANEL_URL_PATH)


def async_unregister_panel(hass: HomeAssistant) -> None:
    """Remove the RESTOCK sidebar panel."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    _LOGGER.info("Unregistered RESTOCK sidebar panel: path=%s", PANEL_URL_PATH)


class RestockOverviewView(HomeAssistantView):
    """Serve the RESTOCK overview page."""

    url = "/api/restock/overview"
    name = "api:restock:overview"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return the overview HTML."""
        return web.Response(text=_overview_html(), content_type="text/html")


class RestockOverviewDataView(HomeAssistantView):
    """Serve RESTOCK overview data."""

    url = "/api/restock/overview/data"
    name = "api:restock:overview:data"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return overview data as JSON."""
        hass: HomeAssistant = request.app["hass"]
        manager = _manager(hass)
        data = _overview_data(manager)
        _LOGGER.debug(
            "Served RESTOCK overview data: containers=%d locations=%d empty=%d low=%d",
            data["summary"]["containers"],
            data["summary"]["locations"],
            data["summary"]["empty"],
            data["summary"]["low"],
        )
        return web.json_response(data)


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
    recent_containers = [_container_summary(container) for container in containers[:12]]

    return {
        "summary": {
            "containers": len(containers),
            "locations": len(manager.locations),
            "total_quantity": total_quantity,
            "empty": len(empty_containers),
            "low": len(low_containers),
        },
        "locations": locations,
        "empty_containers": empty_containers[:8],
        "low_containers": low_containers[:8],
        "recent_containers": recent_containers,
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
    }


def _overview_html() -> str:
    """Return the sidebar panel HTML."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RESTOCK</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f5f5f7;
      --card: rgba(255, 255, 255, 0.86);
      --text: #1d1d1f;
      --muted: #6e6e73;
      --line: rgba(60, 60, 67, 0.18);
      --accent: #007aff;
      --warn: #ff9500;
      --empty: #ff3b30;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #000;
        --card: rgba(28, 28, 30, 0.9);
        --text: #f5f5f7;
        --muted: #98989d;
        --line: rgba(84, 84, 88, 0.55);
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}
    main {{
      width: min(1180px, 100%);
      margin: 0 auto;
      padding: 24px;
    }}
    header {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 22px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{ font-size: 32px; font-weight: 700; letter-spacing: 0; }}
    h2 {{ font-size: 18px; font-weight: 650; }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      background: var(--accent);
      color: white;
      font-weight: 650;
      cursor: pointer;
    }}
    .muted {{ color: var(--muted); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      backdrop-filter: blur(18px);
    }}
    .metric {{
      font-size: 30px;
      font-weight: 750;
      margin-top: 8px;
    }}
    .sections {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
      gap: 18px;
      align-items: start;
    }}
    .stack {{ display: grid; gap: 12px; }}
    .row {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      padding: 12px 0;
      border-top: 1px solid var(--line);
    }}
    .row:first-of-type {{ border-top: 0; }}
    .name {{ font-weight: 650; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      background: rgba(0, 122, 255, 0.12);
      color: var(--accent);
      padding: 4px 9px;
      font-size: 12px;
      font-weight: 650;
      margin-top: 6px;
    }}
    .warn {{ color: var(--warn); }}
    .empty {{ color: var(--empty); }}
    .qty {{ font-weight: 750; text-align: right; }}
    .location {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 0;
      border-top: 1px solid var(--line);
    }}
    .location:first-of-type {{ border-top: 0; }}
    @media (max-width: 850px) {{
      main {{ padding: 16px; }}
      header {{ align-items: flex-start; flex-direction: column; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .sections {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>RESTOCK</h1>
        <p class="muted" id="updated">Loading overview...</p>
      </div>
      <button type="button" onclick="loadOverview()">Refresh</button>
    </header>
    <section class="grid" id="metrics"></section>
    <section class="sections">
      <div class="stack">
        <section class="card">
          <h2>Needs Attention</h2>
          <div id="attention"></div>
        </section>
        <section class="card">
          <h2>Recent Containers</h2>
          <div id="recent"></div>
        </section>
      </div>
      <section class="card">
        <h2>Locations</h2>
        <div id="locations"></div>
      </section>
    </section>
  </main>
  <script>
    const safe = (value) => {{
      const div = document.createElement("div");
      div.textContent = value ?? "";
      return div.innerHTML;
    }};
    const metric = (label, value, klass = "") =>
      `<article class="card"><p class="muted">${{label}}</p><p class="metric ${{klass}}">${{value}}</p></article>`;
    const row = (item, klass = "") => `
      <div class="row">
        <div>
          <p class="name">${{safe(item.name)}}</p>
          <p class="muted">${{safe(item.format || item.state)}} &middot; ${{safe(item.location)}}</p>
          <span class="pill">${{safe(item.tag_id || "no tag")}}</span>
        </div>
        <div class="qty ${{klass}}">${{item.quantity}}<br><span class="muted">${{safe(item.unit)}}</span></div>
      </div>`;
    async function loadOverview() {{
      const response = await fetch("/api/restock/overview/data");
      const data = await response.json();
      const summary = data.summary;
      document.getElementById("updated").textContent = `Updated ${{new Date().toLocaleTimeString()}}`;
      document.getElementById("metrics").innerHTML = [
        metric("Containers", summary.containers),
        metric("Locations", summary.locations),
        metric("Total quantity", summary.total_quantity),
        metric("Low", summary.low, summary.low ? "warn" : ""),
        metric("Empty", summary.empty, summary.empty ? "empty" : "")
      ].join("");
      const attention = [...data.empty_containers.map(item => row(item, "empty")), ...data.low_containers.map(item => row(item, "warn"))];
      document.getElementById("attention").innerHTML = attention.length ? attention.join("") : `<p class="muted">Nothing needs attention.</p>`;
      document.getElementById("recent").innerHTML = data.recent_containers.length
        ? data.recent_containers.map(item => row(item)).join("")
        : `<p class="muted">Scan a container to start building inventory.</p>`;
      document.getElementById("locations").innerHTML = data.locations.length
        ? data.locations.map(location => `<div class="location"><span>${{safe(location.name)}}</span><strong>${{location.containers}}</strong></div>`).join("")
        : `<p class="muted">No locations yet.</p>`;
    }}
    loadOverview();
    window.setInterval(loadOverview, 15000);
  </script>
</body>
</html>"""
