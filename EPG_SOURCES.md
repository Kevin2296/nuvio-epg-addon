# EPG source strategy for Nuvio

The public addon is **not** a private Xtream/M3U processor. It imports curated regional XMLTV feeds, and the customized Nuvio app performs playlist matching locally. Do not commit provider credentials or personal playlist files.

## Source matrix

| Source | Strength | Actual integration in this PR | Rights and limitations |
| --- | --- | --- | --- |
| [EPGShare01](https://epgshare01.online/epgshare01/) | Many regional channel IDs, including European, US and international feeds | **Implemented**: up to 52 configured regional feeds | Free for legal use as stated by provider; do not assume unlimited republication rights. Verify upstream reuse permission before broader public distribution. |
| [IPTV-EPG.org](https://iptv-epg.org/guides) | Country XMLTV feeds, often with additional channel coverage | **Not merged automatically**. Can be configured as an additional EPG source directly in Nuvio/TiviMate | Check provider permissions for replication; a URL for personal IPTV clients is not automatically a redistribution license. |
| [iptv-org/epg](https://github.com/iptv-org/epg) | Open-source tool for collecting EPG from many channel websites | **Not bundled**. Consider it for a private TrueNAS installation | Software source license does not grant rights to scraped schedule data. |
| [TVgids.nl](https://www.tvgids.nl/algemene-voorwaarden) | Dutch schedule descriptions | **Not scraped or redistributed** | Their published terms restrict copying, editing and republication without written permission. |
| Ziggo/Horizon | Broad NL/BE metadata | **Not integrated**; third-party guides mention a Horizon scraper | No verified public redistributable XMLTV endpoint or license in this project. |
| KPN TV | Netherlands guide data | **Not integrated** | KPN states it receives data from broadcasters; no verified publicly licensed KPN XMLTV API in this project. |
| Proximus, BBC, Sky | Potential country-specific gaps | **Not integrated** | Scrapers exist in third-party ecosystems; verify endpoint reliability and rights before use. |

A tutorial referencing scraping ([Cloudje IPTV EPG guide](https://cloudje.eu/iptv-epg-guide/)) is useful for locating possible tools, **not evidence that data from those sites may be republished**.

In the 19 November 2026 full-source smoke test, the Spanish EPGShare01 feed downloaded correctly but had **no current or upcoming listings**. It is therefore omitted from the exported set rather than inventing data. For personal use, the independent [IPTV-EPG.org Spain XMLTV](https://iptv-epg.org/files/epg-es.xml) is another source to configure **directly in Nuvio/TiviMate**, subject to its applicable usage terms. It is not automatically mirrored in this public repository.

## Match behavior and descriptions

1. Preserve original XMLTV channel `id` and primary display name to maintain existing Nuvio/TiviMate `tvg-id` matches.
2. In the Dutch XMLTV output, publish `SBS` as an alternative display-name for `SBS 6` only if it is the only `SBS*` channel in the NL source. Avoid assigning a similarly named wrong station in a different country.
3. The Nuvio Android code already normalizes country prefixes, picture-quality suffixes and punctuation for exact normalized matches. A **general confidence-based fuzzy matcher** is a separate change in Nuvio itself; it is not part of this XMLTV generator.
4. Preserve source-provided descriptions, categories, subtitles and on-screen episode numbers, omitting sensitive URLs and credential-like text. Never infer a programme from a similar channel.
5. A duplicate programme time interval now prefers an entry with richer metadata. Overlapping, different intervals are still rejected rather than silently spliced.
6. A maximum 14-day window is used: if a source only publishes 3 days, then **only 3 days** will appear. `quality.json` reports the actual last show.

## Device-performance design

- `all.xml.gz` deliberately stays a combination of six core regions to avoid a huge initial guide on low-memory Android TV hardware.
- Extended countries are distributed as separate `/epg/<country>.xml.gz` URLs. Add only the countries relevant to the viewer; no full-world download is required.
- The published Nuvio addon catalogues remain six core countries; extended XMLTV files do not create thousands of additional poster/meta/stream endpoint files.
- Country downloads use bounded concurrency. A failed upstream feed is not treated as an empty schedule; existing published data remain available if the complete generation fails.
- GitHub Actions validates pull requests without publishing any IPTV guide data. Before merging test a real Nokia Streaming Box installation, the chosen future-days setting, a match with `SBS`, and `Change EPG` manual overrides.

## Private advanced option

A future TrueNAS service could combine a user-owned Xtream guide with these public sources, save local manual overrides, and optionally back up settings to Nextcloud. Keep that separate from this **public** repository and the actual M3U credentials entirely private.
