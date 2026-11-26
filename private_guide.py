"""Combine provider and regional XMLTV feeds for a private Nuvio installation."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
import urllib.request
import xml.etree.ElementTree as ET
import zlib

from addon import MAX_COMPRESSED, MAX_XML, REGIONS, UTC, USER_AGENT, NoRedirect, iso, parse, write_xmltv
from epg_fusion import combine_programmes, normalized

EPG_ORG_REGIONS = {'NL': 'nl', 'BE': 'be', 'DE': 'de', 'PL': 'pl', 'UK': 'gb', 'US': 'us'}


def presets(region):
    share = REGIONS[region][1]
    feeds = {'epgshare': f'https://epgshare01.online/epgshare01/epg_ripper_{share}.xml.gz'}
    if region == 'PL':
        feeds['epg-ovh'] = 'https://epg.ovh/pltv.gz'
    if region in EPG_ORG_REGIONS:
        code = EPG_ORG_REGIONS[region]
        feeds['iptv-epg'] = f'https://iptv-epg.org/files/epg-{code}.xml.gz'
    if region == 'PL':
        feeds['epg-guru'] = 'https://cdn.epg.guru/7daygracenote/Poland.xml.gz'
        feeds['open-epg'] = 'https://www.open-epg.com/files/poland.xml.gz'
    return feeds


def read_feed(stream):
    prefix = stream.read(2)
    limit = MAX_COMPRESSED if prefix == b'\x1f\x8b' else MAX_XML
    data = prefix + stream.read(limit - len(prefix) + 1)
    if len(data) > limit:
        raise ValueError('guide size limit')
    return data


def download(url):
    address = urlsplit(url)
    if address.scheme != 'https' or not address.hostname or address.username is not None:
        raise ValueError('expected an HTTPS XMLTV URL')
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=45) as response:
        return read_feed(response)


def station_key(name):
    return normalized(name.replace('+', ' plus '))


def matching_schedule(primary, secondary):
    slots = {(p[0], p[1], normalized(p[2])) for p in primary}
    titles = {title for start, stop, raw_title, *_ in secondary
              if (title := normalized(raw_title)) and (start, stop, title) in slots}
    return len(titles) >= 2


def merge(guide, incoming):
    """Keep the first source's IDs and schedule when they can be corroborated."""
    stations = {}
    for channel_id, item in guide.items():
        stations.setdefault(station_key(item['name']), []).append(channel_id)
    incoming_counts = Counter(station_key(item['name']) for item in incoming.values())
    stats = Counter()
    for channel_id, item in incoming.items():
        key = station_key(item['name'])
        target = channel_id
        if target in guide:
            if not key or key != station_key(guide[target]['name']):
                stats['id_conflicts'] += 1
                continue
        else:
            matches = stations.get(key, [])
            if key and len(matches) == 1 and incoming_counts[key] == 1 and matching_schedule(
                    guide[matches[0]]['programmes'], item['programmes']):
                target = matches[0]
                stats['matched_different_id'] += 1
            else:
                guide[channel_id] = item
                stats['channels_added'] += 1
                stats['programmes_added'] += len(item['programmes'])
                continue
        guide[target]['programmes'], counts = combine_programmes(
            guide[target]['programmes'], item['programmes'])
        stats.update(counts)
        stats['channels_merged'] += 1
    return dict(stats)


def source_plan(region, requested):
    feeds = presets(region)
    plan = []
    seen = set()
    for source in requested or ['regional']:
        for item in (feeds if source == 'regional' else [source]):
            if item in seen:
                continue
            seen.add(item)
            kind, _, value = item.partition('=')
            if item in feeds:
                plan.append((item, None, feeds[item]))
            elif kind in {'file', 'env'} and value:
                plan.append((f'{kind}-{len(plan) + 1}', kind, value))
            else:
                raise ValueError('unknown source for region')
    return plan


def generate(region, output, requested=None, now=None):
    now = now or datetime.now(UTC)
    guide = {}
    reports = {}
    for label, kind, value in source_plan(region, requested):
        try:
            if kind == 'file':
                with Path(value).open('rb') as stream:
                    raw = read_feed(stream)
            else:
                raw = download(os.environ[value] if kind == 'env' else value)
            channels, _ = parse(raw, now)
        except (OSError, ValueError, KeyError, EOFError, ET.ParseError, zlib.error):
            print(f'{label}: unavailable or no usable programmes', file=sys.stderr)
            if kind:
                raise ValueError('required guide source unavailable') from None
            reports[label] = {'status': 'unavailable'}
            continue
        reports[label] = {'status': 'ok', 'channels': len(channels), **merge(guide, channels)}
    if not guide:
        raise ValueError('no usable guide sources')

    report = {
        'region': region,
        'generated_at': iso(now),
        'channels_with_schedule': len(guide),
        'channels_on_air_now': sum(
            any(p[0] <= now < p[1] for p in channel['programmes']) for channel in guide.values()),
        'programmes': sum(len(channel['programmes']) for channel in guide.values()),
        'latest_programme_end': iso(max(p[1] for channel in guide.values() for p in channel['programmes'])),
        'sources': reports,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temp:
        draft = Path(temp) / output.name
        write_xmltv(draft, guide, region)
        draft.replace(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', type=str.upper, choices=REGIONS, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Private .xml.gz output path')
    parser.add_argument('--source', action='append', metavar='PRESET|file=PATH|env=NAME',
                        help='Repeat in priority order. regional expands to the region presets.')
    args = parser.parse_args()
    if not args.output.name.endswith('.xml.gz'):
        parser.error('--output must end in .xml.gz')
    try:
        report = generate(args.region, args.output, args.source)
    except (OSError, ValueError):
        print('Private guide generation failed', file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
