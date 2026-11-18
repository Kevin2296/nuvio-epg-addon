"""Generate a static Stremio/Nuvio guide addon from public XMLTV sources only.

No server, provider credentials, playlist parsing, or third-party dependencies.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
from html import escape
import io
import json
from pathlib import Path
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = timezone.utc
PAGE_SIZE = 100
WINDOW_DAYS = 14
CATALOG_REGIONS = frozenset({'NL', 'BE', 'DE', 'PL', 'US', 'UK'})
MAX_COMPRESSED = 32 * 1024 * 1024
MAX_XML = 160 * 1024 * 1024
BASE = 'https://raw.githubusercontent.com/Kevin2296/nuvio-epg-addon/epg-data/public'
USER_AGENT = 'Mozilla/5.0 (Linux; Android 12; Android TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
REGIONS = {
    'NL': ('Nederland', 'NL1', 'Europe/Amsterdam'),
    'BE': ('België', 'BE2', 'Europe/Brussels'),
    'DE': ('Duitsland', 'DE1', 'Europe/Berlin'),
    'PL': ('Polen', 'PL1', 'Europe/Warsaw'),
    'US': ('Verenigde Staten', 'US2', 'America/New_York'),
    'UK': ('Verenigd Koninkrijk', 'UK1', 'Europe/London'),
    'FR': ('Frankrijk', 'FR1', 'Europe/Paris'),
    'ES': ('Spanje', 'ES1', 'Europe/Madrid'),
    'IT': ('Italië', 'IT1', 'Europe/Rome'),
    'PT': ('Portugal', 'PT1', 'Europe/Lisbon'),
    'AT': ('Oostenrijk', 'AT1', 'Europe/Vienna'),
    'CH': ('Zwitserland', 'CH1', 'Europe/Zurich'),
    'LU': ('Luxemburg', 'LU1', 'Europe/Luxembourg'),
    'IE': ('Ierland', 'IE1', 'Europe/Dublin'),
    'CZ': ('Tsjechië', 'CZ1', 'Europe/Prague'),
    'SK': ('Slowakije', 'SK1', 'Europe/Bratislava'),
    'HU': ('Hongarije', 'HU1', 'Europe/Budapest'),
    'RO': ('Roemenië', 'RO1', 'Europe/Bucharest'),
    'HR': ('Kroatië', 'HR1', 'Europe/Zagreb'),
    'RS': ('Servië', 'RS1', 'Europe/Belgrade'),
    'BA': ('Bosnië en Herzegovina', 'BA1', 'Europe/Sarajevo'),
    'BG': ('Bulgarije', 'BG1', 'Europe/Sofia'),
    'GR': ('Griekenland', 'GR1', 'Europe/Athens'),
    'TR': ('Turkije', 'TR3', 'Europe/Istanbul'),
    'DK': ('Denemarken', 'DK1', 'Europe/Copenhagen'),
    'SE': ('Zweden', 'SE1', 'Europe/Stockholm'),
    'NO': ('Noorwegen', 'NO1', 'Europe/Oslo'),
    'FI': ('Finland', 'FI1', 'Europe/Helsinki'),
    'CA': ('Canada', 'CA2', 'America/Toronto'),
    'AU': ('Australië', 'AU1', 'Australia/Sydney'),
    'NZ': ('Nieuw-Zeeland', 'NZ1', 'Pacific/Auckland'),
    'BR': ('Brazilië', 'BR1', 'America/Sao_Paulo'),
    'MX': ('Mexico', 'MX1', 'America/Mexico_City'),
    'AR': ('Argentinië', 'AR1', 'America/Argentina/Buenos_Aires'),
    'CL': ('Chili', 'CL1', 'America/Santiago'),
    'CO': ('Colombia', 'CO1', 'America/Bogota'),
    'EC': ('Ecuador', 'EC1', 'America/Guayaquil'),
    'PE': ('Peru', 'PE1', 'America/Lima'),
    'UY': ('Uruguay', 'UY1', 'America/Montevideo'),
    'JP': ('Japan', 'JP1', 'Asia/Tokyo'),
    'KR': ('Zuid-Korea', 'KR1', 'Asia/Seoul'),
    'HK': ('Hongkong', 'HK1', 'Asia/Hong_Kong'),
    'SG': ('Singapore', 'SG1', 'Asia/Singapore'),
    'MY': ('Maleisië', 'MY1', 'Asia/Kuala_Lumpur'),
    'ID': ('Indonesië', 'ID1', 'Asia/Jakarta'),
    'IN': ('India', 'IN1', 'Asia/Kolkata'),
    'IL': ('Israël', 'IL1', 'Asia/Jerusalem'),
    'AE': ('Verenigde Arabische Emiraten', 'AE1', 'Asia/Dubai'),
    'ZA': ('Zuid-Afrika', 'ZA1', 'Africa/Johannesburg'),
    'LV': ('Letland', 'LV1', 'Europe/Riga'),
    'LT': ('Litouwen', 'LT1', 'Europe/Vilnius'),
    'CY': ('Cyprus', 'CY1', 'Asia/Nicosia'),
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url: str) -> bytes:
    """Only code-defined public feed URLs are passed here; no config URL inputs."""
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=45) as response:
        if response.status != 200:
            raise ValueError('download status')
        raw = response.read(MAX_COMPRESSED + 1)
    if len(raw) > MAX_COMPRESSED or not raw.startswith(b'\x1f\x8b'):
        raise ValueError('download format or size')
    return raw


def xml_bytes(raw: bytes) -> bytes:
    if raw.startswith(b'\x1f\x8b'):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(MAX_XML + 1)
    if len(raw) > MAX_XML:
        raise ValueError('XML size')
    # XMLTV's conventional external DTD is metadata, not fetched or processed.
    # Only that exact declaration is stripped; internal subsets/entities stay forbidden.
    raw = re.sub(rb'<!DOCTYPE\s+tv\s+SYSTEM\s+[\"\x27]xmltv\.dtd[\"\x27]\s*>', b'', raw, flags=re.I)
    # Reject other DTDs, entities and alternate-width encodings before parsing.
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper() or b'\x00' in raw:
        raise ValueError('unsafe XML')
    return raw


def timestamp(value: str) -> datetime:
    """Accept XMLTV's optional seconds, but require an explicit timezone."""
    if not re.fullmatch(r'\d{12}(\d{2})? [+-]\d{4}', value):
        raise ValueError('timestamp')
    fmt = '%Y%m%d%H%M%S %z' if len(value.split()[0]) == 14 else '%Y%m%d%H%M %z'
    return datetime.strptime(value, fmt).astimezone(UTC)


def text(element, name, limit=200):
    return ' '.join((element.findtext(name) or '').split())[:limit]


# Reject potentially sensitive source strings, while retaining ordinary programme summaries.
SENSITIVE_DETAIL = re.compile(
    r'(?i)(?:https?://|rtsp://|rtmp://|private provider|'
    r'\\b(?:password|passwd|username|api[_-]?key|token|xtream)\\s*[:=])'
)


def safe_detail(value: str, limit: int) -> str:
    value = ' '.join(value.split())
    if SENSITIVE_DETAIL.search(value):
        return ''
    return value[:limit]


def parse(raw: bytes, now: datetime):
    """Return whitelisted channel names and valid schedules; never pass URLs through."""
    names, programmes = {}, defaultdict(list)
    end = now + timedelta(days=WINDOW_DAYS)
    invalid = 0
    raw = xml_bytes(raw)
    root_tag = None
    for event, node in ET.iterparse(io.BytesIO(raw), events=('start', 'end')):
        if root_tag is None:
            root_tag = node.tag
            if root_tag != 'tv':
                raise ValueError('XML root')
        if event != 'end':
            continue
        if node.tag == 'channel':
            cid = node.get('id', '')
            name = text(node, 'display-name', 100)
            if cid and len(cid) <= 256 and name:
                names[cid] = name
            node.clear()
        elif node.tag == 'programme':
            try:
                start, stop = timestamp(node.get('start', '')), timestamp(node.get('stop', ''))
                title = text(node, 'title', 200)
                cid = node.get('channel', '')
                if not title or not cid or len(cid) > 256 or stop <= start:
                    raise ValueError('programme')
                if stop > now and start < end:
                    # Preserve only plain textual XMLTV fields Nuvio actually understands.
                    # External icons, remote URLs and source-specific extensions stay private.
                    desc = safe_detail(text(node, 'desc', 1600), 600)
                    category = safe_detail(text(node, 'category', 90), 80)
                    subtitle = safe_detail(text(node, 'sub-title', 160), 140)
                    episode_node = node.find('episode-num')
                    episode = (safe_detail(''.join(episode_node.itertext()), 40)
                               if episode_node is not None and
                               episode_node.get('system') in (None, 'onscreen') else '')
                    programmes[cid].append((start, stop, title, desc, category, subtitle, episode))
            except ValueError:
                invalid += 1
            node.clear()
    result = {}
    overlaps = 0
    for cid, items in programmes.items():
        if cid not in names:
            continue
        accepted = []
        last_stop = None
        for start, stop, title in sorted(set(items)):
            if last_stop is not None and start < last_stop:
                overlaps += 1
                continue
            accepted.append((start, stop, title))
            last_stop = stop
        if accepted:
            result[cid] = {'name': names[cid], 'programmes': accepted}
    if not result:
        raise ValueError('no usable programmes')
    current = sum(any(p[0] <= now < p[1] for p in ch['programmes']) for ch in result.values())
    with_desc = sum(any(p[3] for p in ch['programmes']) for ch in result.values())
    latest = max((p[1] for ch in result.values() for p in ch['programmes']), default=now)
    return result, {'declared_channels': len(names), 'channels_with_schedule': len(result),
                    'channels_on_air_now': current, 'channels_without_current_programme': len(result) - current,
                    'channels_with_descriptions': with_desc,
                    'latest_programme_end': iso(latest),
                    'invalid_programmes': invalid, 'overlaps_removed': overlaps}


def iso(value):
    return value.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def channel_id(region, source_id):
    # IDs must be route safe even when XMLTV IDs contain slashes, dots or Unicode.
    return 'kepg_' + region.lower() + '_' + hashlib.sha256(source_id.encode()).hexdigest()[:24]


def write_json(output, path, obj):
    destination = output / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')),
                           encoding='utf-8', newline='\n')


def poster(output, cid, region, name):
    destination = output / 'assets' / (cid + '.svg')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic, local vector cards: clients do not contact channel-logo trackers.
    title = escape(name[:25])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
<rect width="400" height="400" rx="28" fill="#101b2b"/><rect x="28" y="28" width="70" height="38" rx="10" fill="#2dd4bf"/>
<text x="63" y="54" font-family="sans-serif" font-size="23" font-weight="bold" text-anchor="middle" fill="#101b2b">{region}</text>
<path d="M48 112H352M48 144H280M48 176H320" stroke="#33485e" stroke-width="12" stroke-linecap="round"/>
<text x="28" y="253" font-family="sans-serif" font-size="23" font-weight="bold" fill="#f0f5ff">{title}</text>
<text x="28" y="346" font-family="sans-serif" font-size="18" fill="#9fbdcf">TV-GIDS · EPG</text></svg>'''
    destination.write_text(svg, encoding='utf-8')


def description(region, programmes, now):
    try:
        zone = ZoneInfo(REGIONS[region][2])
        zone_name = REGIONS[region][2]
    except ZoneInfoNotFoundError:
        # Windows may not have an IANA timezone database; always label UTC honestly.
        zone, zone_name = UTC, 'UTC'
    lines = ['TV-gids · geen videostreams.',
             'Bijgewerkt: ' + now.strftime('%d-%m-%Y %H:%M UTC'),
             'Tijden hieronder: ' + zone_name + '.', '']
    for program in programmes[:12]:
        start, stop, title = program[:3]
        lines.append(start.astimezone(zone).strftime('%d-%m %H:%M') + '–' +
                     stop.astimezone(zone).strftime('%H:%M') + '  ' + title)
        if len(program) >= 4 and program[3]:
            lines.append('  ' + program[3][:120])
    lines.extend(['', 'Gebruik de XMLTV-link uit de README voor de geïntegreerde Live TV-gids.'])
    return '\n'.join(lines)


def xmltv(channels):
    root = ET.Element('tv', {'generator-info-name': 'Nuvio EPG Addon'})
    for cid, item in channels.items():
        ch = ET.SubElement(root, 'channel', {'id': cid})
        ET.SubElement(ch, 'display-name').text = item['name']
    for cid, item in channels.items():
        for program in item['programmes']:
            start, stop, title = program[:3]
            desc, category, subtitle, episode = (list(program[3:]) + ['', '', '', ''])[:4]
            p = ET.SubElement(root, 'programme', {
                'channel': cid, 'start': start.strftime('%Y%m%d%H%M%S +0000'),
                'stop': stop.strftime('%Y%m%d%H%M%S +0000')})
            ET.SubElement(p, 'title').text = title
            if subtitle:
                ET.SubElement(p, 'sub-title').text = subtitle
            if desc:
                ET.SubElement(p, 'desc').text = desc
            if category:
                ET.SubElement(p, 'category').text = category
            if episode:
                ET.SubElement(p, 'episode-num', {'system': 'onscreen'}).text = episode
    return gzip.compress(ET.tostring(root, encoding='utf-8', xml_declaration=True), mtime=0)


def build(output: Path, feeds: dict, now: datetime, base=BASE, source_status=None):
    """Write a complete generation into a NEW directory. Caller publishes only on success."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('output must be empty')
    if not base.startswith('https://') or '?' in base or '#' in base:
        raise ValueError('public base URL')
    base = base.rstrip('/')
    catalogs = []
    combined = {}
    duplicate_ids = 0
    report = {'generated_at': iso(now), 'window_hours': WINDOW_DAYS * 24,
              'window_days': WINDOW_DAYS, 'regions': {},
              'guide_only': True, 'source_status': source_status or {}}
    for region in REGIONS:
        if region not in feeds:
            continue
        channels, counts = parse(feeds[region], now)
        for source_id, item in channels.items():
            if source_id not in combined:
                combined[source_id] = item
            else:
                duplicate_ids += 1
        report['regions'][region] = counts
        slug = region.lower()
        (output / 'epg').mkdir(exist_ok=True)
        (output / 'epg' / f'{slug}.xml.gz').write_bytes(xmltv(channels))
        # Extended international XMLTV coverage without enormous addon catalogues.
        if region not in CATALOG_REGIONS:
            continue
        label = REGIONS[region][0]
        catalogs.append({'id': slug, 'type': 'tv', 'name': 'TV-gids · ' + label,
                         'pageSize': PAGE_SIZE, 'extra': [{'name': 'skip'}, {'name': 'date'}]})
        metas = []
        for source_id, item in sorted(channels.items(), key=lambda row: row[1]['name'].casefold()):
            cid = channel_id(region, source_id)
            poster(output, cid, region, item['name'])
            videos = [{'id': cid + '_epg_' + str(int(p[0].timestamp())),
                       'title': p[2], 'released': iso(p[0]), 'startTime': iso(p[0]),
                       'endTime': iso(p[1]), 'runtime': str(int((p[1] - p[0]).total_seconds() // 60)) + ' min',
                       **({'description': p[3]} if p[3] else {})}
                      for p in item['programmes']]
            meta = {'id': cid, 'type': 'tv', 'name': item['name'], 'country': region,
                    'poster': base + '/assets/' + cid + '.svg', 'posterShape': 'square',
                    'genres': ['TV-gids', label], 'description': description(region, item['programmes'], now),
                    'behaviorHints': {'isLive': True, 'hasScheduledVideos': True}, 'videos': videos}
            metas.append(meta)
            write_json(output, f'meta/tv/{cid}.json', {'meta': meta, 'cacheMaxAge': 900})
            # Explicit empty response: no stream credentials ever enter this addon.
            write_json(output, f'stream/tv/{cid}.json', {'streams': []})
        # Standard discovery + EPG day pages, including exact terminal-page offsets.
        # A short page is not terminal in the addon protocol.
        skips = list(range(0, len(metas), PAGE_SIZE)) + [len(metas)]
        for skip in dict.fromkeys(skips):
            page = metas[skip:skip + PAGE_SIZE]
            previews = [{k: v for k, v in meta.items() if k != 'videos'} for meta in page]
            payload = {'metas': previews, 'cacheMaxAge': 900}
            if skip == 0:
                write_json(output, f'catalog/tv/{slug}.json', payload)
            write_json(output, f'catalog/tv/{slug}/skip={skip}.json', payload)
            # Covers midnight crossings and the entire publication window.
            for offset in range(-1, WINDOW_DAYS + 2):
                day = (now + timedelta(days=offset)).date()
                start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
                stop = start + timedelta(days=1)
                detailed = [{**meta, 'videos': [v for v in meta['videos']
                                              if v['endTime'] > iso(start) and v['startTime'] < iso(stop)]}
                            for meta in page]
                result = {'metas': previews, 'metasDetailed': detailed, 'cacheMaxAge': 900}
                args = f'date={day}'
                if skip == 0:
                    write_json(output, f'catalog/tv/{slug}/{args}.json', result)
                for extra in (f'{args}&skip={skip}', f'skip={skip}&{args}'):
                    write_json(output, f'catalog/tv/{slug}/{extra}.json', result)
    if not catalogs:
        raise ValueError('no healthy regions')
    (output / 'epg' / 'all.xml.gz').write_bytes(xmltv(combined))
    report['combined_channels'] = len(combined)
    report['duplicate_xmltv_ids_first_source_wins'] = duplicate_ids
    manifest = {
        'id': 'com.kevin2296.nuvio.epg', 'version': '1.1.0', 'name': 'Nuvio EPG · TV-gids',
        'description': 'Internationale tv-gids. Alleen gidsinformatie; geen IPTV-login of videostreams. '
                       'Gebruik de XMLTV-links uit de README voor de ingebouwde Live TV-gids.',
        'resources': ['catalog', 'meta', 'stream'], 'types': ['tv'], 'idPrefixes': ['kepg_'],
        'catalogs': catalogs, 'behaviorHints': {'epgProvider': True, 'configurable': False},
        'logo': metas[0]['poster'],
    }
    write_json(output, 'manifest.json', manifest)
    write_json(output, 'quality.json', report)
    (output / '.nojekyll').write_text('')
    return report


def generate(output: Path, now=None):
    now = now or datetime.now(UTC)
    feeds, status = {}, {}
    for region, (_, source, _) in REGIONS.items():
        try:
            raw = fetch(f'https://epgshare01.online/epgshare01/epg_ripper_{source}.xml.gz')
            parse(raw, now)  # Validate before considering this source healthy.
            feeds[region], status[region] = raw, 'fresh'
        except Exception:
            # Exception messages can contain URLs or response data: never print them.
            try:
                raw = fetch(BASE + '/epg/' + region.lower() + '.xml.gz')
                parse(raw, now)
                feeds[region], status[region] = raw, 'previous-public-snapshot'
            except Exception:
                status[region] = 'unavailable'
        print(region + ': ' + status[region], flush=True)
    # All-source failure leaves the existing published branch untouched.
    return build(output, feeds, now, source_status=status)


def main():
    parser = argparse.ArgumentParser(description='Generate public EPG addon JSON and XMLTV')
    parser.add_argument('--output', type=Path, default=Path('public'))
    args = parser.parse_args()
    try:
        report = generate(args.output)
        print('Generated ' + str(sum(r['channels_with_schedule'] for r in report['regions'].values())) + ' guide channels')
    except Exception:
        print('Generation failed; previous published snapshot must be retained', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
