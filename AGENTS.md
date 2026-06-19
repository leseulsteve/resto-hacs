# Codex Instructions For RESTOCK

## Publish Integration

When Steve asks to publish the integration, publish a HACS-visible RESTOCK
release:

1. Update `custom_components/restock/manifest.json` to the requested semantic
   version.
2. Add a short entry to `CHANGELOG.md`.
3. Validate Python and JSON locally.
4. Scan staged content for secrets.
5. Commit as `Release VERSION`.
6. Tag as `vVERSION`.
7. Push `main` and tags to origin.

Do not add or push files under `scripts/`.

Keep README files short. They should mainly describe RESTOCK as a personal,
experimental project.
