# Nuvio EPG Addon — development source

This repository is a development handoff, **not an installable addon release**. It contains an experimental native EPG source-selection module for the customized NuvioPlusIPTV fork and a patch for integrating it. No credentials, playlists, signing keys or generated guide data belong here.

## Current state

- Native prototype: country-source selection, existing XMLTV matching/cache integration, count-only guide coverage and refresh controls.
- Source links: NL, BE, DE, PL, US, UK. Adult sources remain manual.
- Standalone quality/preset checks passed; public-feed GET probes returned HTTP 200 and gzip headers. Full programme contents were not validated.
- No completed APK build, device test, or hosted `manifest.json` installation endpoint is provided.

## Addon compatibility

The current Stremio addon protocol supports EPG using a TV catalog with an optional `date` parameter, `epgProvider` in manifest behavior hints and programmes with `startTime` / `endTime`. See https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/epg.md .

The inspected local NuvioPlusIPTV fork does not currently preserve these schedule fields or implement the matching guide-catalog integration in its addon path. Therefore a standards-compliant addon could expose metadata/catalog content, but installing it alone would not populate this fork's native IPTV timeline or match its private IPTV channels. A client bridge is still required for that behavior. A native JS scraper plugin is a separate interface and is not a confirmed workaround for this limitation.

GitHub repositories store code. GitHub Pages can serve generated static addon JSON; it does not execute an always-running XMLTV aggregator. Scheduled generation would need a workflow or another service and client compatibility verification. This repository deliberately makes no installable-addon claim and publishes no fake manifest.

## Integration

Read `PRIVATE_EPG_HUB.md`. The `PRIVATE_EPG_HUB.patch` contains only this feature's edits. Apply it in a separate branch of the intended fork after reviewing existing changes; check for conflicts rather than replacing files. Resume the Android build when the workstation has enough free memory.

## Privacy

Only source and documentation are included. Keep Xtream credentials, M3U files, private guide URLs, Nextcloud app passwords, runtime reports, and Android signing material outside GitHub. Public EPG downloads reveal the requesting device's IP address to the source host. Existing app synchronization preferences are not changed by this prototype.

This repository hosts development source only. GitHub Pages hosting and an installable addon endpoint are not enabled.
