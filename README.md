# RESTOCK

RESTOCK is a Home Assistant custom integration for tracking physical inventory
containers with NFC/RFID tags and an ESPHome M5Dial scanner.

## Status

RESTOCK is a personal experiment and is shared as-is. It is not a polished or
official Home Assistant integration, and it should be used for testing and
learning rather than relied on for critical inventory tracking.

## Personal HACS Installation

HACS can install RESTOCK as a custom repository for your own Home Assistant
instance. The repository does not need to be submitted to the HACS default store,
but HACS must be able to read it from GitHub.

Important: HACS does not support truly private GitHub repositories. If the repo
must stay private, use the manual development install below instead.

1. Push this folder to a GitHub repository that HACS can access.
2. In Home Assistant, open **HACS > Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Add your repository URL and select **Integration** as the category.
5. Install **RESTOCK** from HACS.
6. Restart Home Assistant.
7. Add RESTOCK from **Settings > Devices & services**.

## Versioning And Updates

RESTOCK uses semantic versions in
`custom_components/restock/manifest.json`. HACS reads GitHub releases and will
surface new versions in Home Assistant as an update entity and in the Settings
update UI when this integration is installed through HACS.

To publish a new version:

```bash
python3 scripts/bump_version.py 0.1.1
git add custom_components/restock/manifest.json CHANGELOG.md
git commit -m "Release 0.1.1"
git tag v0.1.1
git push origin main --tags
```

The GitHub release workflow checks that the tag, such as `v0.1.1`, matches the
manifest version, such as `0.1.1`, before creating a release.

In Home Assistant, make sure HACS update entities are enabled. Once HACS sees a
new GitHub release, Home Assistant can show RESTOCK as an available update. For
extra reminders, create an automation from the RESTOCK/HACS update entity that
sends a persistent notification when its state changes to `on`.

## M5Dial

The ESPHome configuration lives in `esphome/m5dial/m5dial-inventory.yaml`.
Compile and install that config separately through ESPHome.

The default RESTOCK ESPHome action prefix is `m5dial_inventory`, which matches
the node name `m5dial-inventory`. Change it in RESTOCK options if Home Assistant
registers the ESPHome services with a different prefix.

## Development Install

For local testing, copy `custom_components/restock` into your Home Assistant
config directory:

```text
config/custom_components/restock
```

Then restart Home Assistant and add RESTOCK from **Settings > Devices & services**.

## Mock API

`restock.mock_api` is a temporary service that publishes a
`restock.mock_api_response` event with mock item and location data. It is a
placeholder for the future external JSON API.
