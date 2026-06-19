class RestockPanel extends HTMLElement {
  connectedCallback() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._data = null;
    this._error = "";
    this._render();
    this._load();
    this._timer = window.setInterval(() => this._load(), 15000);
  }

  disconnectedCallback() {
    window.clearInterval(this._timer);
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.shadowRoot) {
      return;
    }
    if (!this._loadedOnce) {
      this._load();
    }
  }

  async _load() {
    if (!this._hass) {
      return;
    }
    try {
      this._data = await this._hass.callWS({ type: "restock/overview" });
      this._error = "";
      this._loadedOnce = true;
    } catch (err) {
      this._error = err?.message || "Could not load RESTOCK overview.";
    }
    this._render();
  }

  _render() {
    const data = this._data;
    if (!this.shadowRoot) {
      return;
    }
    const summary = data?.summary || {};
    const containers = data?.containers || [];
    const locations = data?.locations || [];
    const logbook = data?.logbook || [];
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          min-height: 100%;
          color: var(--primary-text-color);
          background: var(--primary-background-color);
          font-family: var(--paper-font-body1_-_font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
        }
        * { box-sizing: border-box; }
        main {
          width: min(1180px, 100%);
          margin: 0 auto;
          padding: 24px;
        }
        header {
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 22px;
        }
        h1, h2, h3, p { margin: 0; }
        h1 { font-size: 32px; font-weight: 720; letter-spacing: 0; }
        h2 { font-size: 18px; font-weight: 650; }
        button {
          border: 0;
          border-radius: 999px;
          padding: 10px 16px;
          background: var(--primary-color);
          color: var(--text-primary-color);
          font-weight: 650;
          cursor: pointer;
        }
        .muted { color: var(--secondary-text-color); }
        .error {
          margin-bottom: 16px;
          padding: 12px 14px;
          border-radius: 12px;
          background: rgba(244, 67, 54, 0.14);
          color: var(--error-color, #f44336);
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(120px, 1fr));
          gap: 12px;
          margin-bottom: 18px;
        }
        .card {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 14px;
          padding: 16px;
          box-shadow: var(--ha-card-box-shadow, none);
        }
        .metric {
          font-size: 30px;
          font-weight: 750;
          margin-top: 8px;
        }
        .sections {
          display: grid;
          grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
          gap: 18px;
          align-items: start;
        }
        .stack { display: grid; gap: 12px; }
        .row {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 12px;
          align-items: center;
          padding: 12px 0;
          border-top: 1px solid var(--divider-color);
        }
        .row:first-of-type { border-top: 0; }
        .name { font-weight: 650; overflow-wrap: anywhere; }
        .pill {
          display: inline-flex;
          align-items: center;
          border-radius: 999px;
          background: color-mix(in srgb, var(--primary-color) 14%, transparent);
          color: var(--primary-color);
          padding: 4px 9px;
          font-size: 12px;
          font-weight: 650;
          margin-top: 6px;
        }
        .warn { color: var(--warning-color, #ff9800); }
        .empty { color: var(--error-color, #f44336); }
        .qty { font-weight: 750; text-align: right; white-space: nowrap; }
        .location {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          padding: 10px 0;
          border-top: 1px solid var(--divider-color);
        }
        .location:first-of-type { border-top: 0; }
        .log {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 8px;
          padding: 11px 0;
          border-top: 1px solid var(--divider-color);
        }
        .log:first-of-type { border-top: 0; }
        .log-action { font-weight: 650; }
        .log-time { font-size: 12px; color: var(--secondary-text-color); white-space: nowrap; }
        @media (max-width: 850px) {
          main { padding: 16px; }
          header { align-items: flex-start; flex-direction: column; }
          .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
          .sections { grid-template-columns: 1fr; }
        }
      </style>
      <main>
        <header>
          <div>
            <h1>RESTOCK</h1>
            <p class="muted">${data ? `Updated ${new Date().toLocaleTimeString()}` : "Loading overview..."}</p>
          </div>
          <button type="button" id="refresh">Refresh</button>
        </header>
        ${this._error ? `<div class="error">${this._safe(this._error)}</div>` : ""}
        <section class="grid">
          ${this._metric("Containers", summary.containers ?? 0)}
          ${this._metric("Locations", summary.locations ?? 0)}
          ${this._metric("Total quantity", summary.total_quantity ?? 0)}
          ${this._metric("Low", summary.low ?? 0, summary.low ? "warn" : "")}
          ${this._metric("Empty", summary.empty ?? 0, summary.empty ? "empty" : "")}
        </section>
        <section class="sections">
          <div class="stack">
            <section class="card">
              <h2>Containers</h2>
              ${containers.length ? containers.map((item) => this._containerRow(item)).join("") : `<p class="muted">Scan a container to start building inventory.</p>`}
            </section>
            <section class="card">
              <h2>Logbook</h2>
              ${logbook.length ? logbook.map((entry) => this._logRow(entry)).join("") : `<p class="muted">No actions recorded yet.</p>`}
            </section>
          </div>
          <div class="stack">
            <section class="card">
              <h2>Needs Attention</h2>
              ${this._attentionRows(data)}
            </section>
            <section class="card">
              <h2>Locations</h2>
              ${locations.length ? locations.map((location) => this._locationRow(location)).join("") : `<p class="muted">No locations yet.</p>`}
            </section>
          </div>
        </section>
      </main>
    `;
    this.shadowRoot.getElementById("refresh")?.addEventListener("click", () => this._load());
  }

  _metric(label, value, klass = "") {
    return `<article class="card"><p class="muted">${this._safe(label)}</p><p class="metric ${klass}">${this._safe(value)}</p></article>`;
  }

  _containerRow(item, klass = "") {
    return `
      <div class="row">
        <div>
          <p class="name">${this._safe(item.name)}</p>
          <p class="muted">${this._safe(item.format || item.state)} &middot; ${this._safe(item.location)}</p>
          <span class="pill">${this._safe(item.tag_id || "no tag")}</span>
        </div>
        <div class="qty ${klass}">${this._safe(item.quantity)}<br><span class="muted">${this._safe(item.unit)}</span></div>
      </div>
    `;
  }

  _attentionRows(data) {
    const empty = data?.empty_containers || [];
    const low = data?.low_containers || [];
    const rows = [
      ...empty.map((item) => this._containerRow(item, "empty")),
      ...low.map((item) => this._containerRow(item, "warn")),
    ];
    return rows.length ? rows.join("") : `<p class="muted">Nothing needs attention.</p>`;
  }

  _locationRow(location) {
    return `<div class="location"><span>${this._safe(location.name)}</span><strong>${this._safe(location.containers)}</strong></div>`;
  }

  _logRow(entry) {
    return `
      <div class="log">
        <div>
          <p class="log-action">${this._safe(entry.action)}</p>
          <p class="muted">${this._safe(entry.message)}</p>
        </div>
        <time class="log-time">${this._formatTime(entry.created_at)}</time>
      </div>
    `;
  }

  _formatTime(value) {
    if (!value) {
      return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return this._safe(value);
    }
    return this._safe(date.toLocaleString());
  }

  _safe(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
  }
}

if (!customElements.get("restock-panel")) {
  customElements.define("restock-panel", RestockPanel);
}
