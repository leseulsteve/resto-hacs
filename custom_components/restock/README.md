# RESTOCK

RESTOCK is a Home Assistant custom integration for tracking physical inventory
containers by NFC/RFID tag.

## Status

RESTOCK is a personal experiment and is provided as-is. Use it for testing,
learning, and iteration, not for critical inventory tracking.

## Install

Copy `custom_components/restock` into your Home Assistant config directory and
restart Home Assistant. Then add RESTOCK from **Settings > Devices & services**.

## Entities

RESTOCK creates:

- one quantity sensor per container
- one location sensor per container
- one state sensor per container
- one location entity per configured location, showing the number of containers there

## Services

- `restock.create_location`
- `restock.create_container`
- `restock.update_container`
- `restock.fill_container`
- `restock.remove_items`
- `restock.scan_container`
- `restock.mock_api`

`restock.mock_api` is a temporary stand-in for the future external JSON API. It
fires a `restock.mock_api_response` event with mock `items` and `locations`.

## M5Dial flow

The M5Dial config fires `esphome.restock_scan` with:

```yaml
tag_id: "04-AA-BB-CC"
```

RESTOCK looks up the tag:

- Unknown tag: RESTOCK calls the M5Dial `show_create_container` ESPHome action
  with mock API item/location lists. The dial lets you select item, count, and
  location, then fires `esphome.restock_create_container`.
- Known tag: RESTOCK calls `show_known_container` with the current container
  data and location list. The dial lets you change count and location, then
  fires `esphome.restock_update_container`.

The default ESPHome action prefix is `m5dial_inventory`, which matches the node
name `m5dial-inventory`. Change it in the integration options if the ESPHome
service names are different.
