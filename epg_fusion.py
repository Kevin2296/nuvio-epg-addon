"""Conservative XMLTV source fusion.

Match only stable XMLTV identifiers with compatible names and timeslots.
Never guess between broadcasters based solely on an abbreviated name.
"""
from __future__ import annotations

import re
import unicodedata

QUALITY = re.compile(r'\b(?:hd|fhd|uhd|sd|4k|8k|hevc|backup|1080p|720p)\b', re.I)


def normalized(name: str) -> str:
    name = unicodedata.normalize('NFKD', name).casefold()
    name = ''.join(ch for ch in name if not unicodedata.combining(ch))
    name = QUALITY.sub(' ', name)
    return ''.join(ch for ch in name if ch.isalnum())


def details_score(item: tuple) -> tuple:
    fields = list(item[3:]) + ['', '', '', '']
    desc, category, subtitle, episode = fields[:4]
    return (bool(desc), len(desc), bool(subtitle), bool(category), bool(episode))


def combine_programmes(primary: list, secondary: list) -> tuple[list, dict]:
    """Append genuinely missing, nonoverlapping broadcasts; enrich same-title duplicates.

    The main feed remains authoritative about programme identity and times.
    A secondary broadcast with the same time but different title never replaces it.
    """
    accepted = list(sorted(primary, key=lambda x: (x[0], x[1])))
    enriched = 0
    added = 0
    conflicts = 0
    for candidate in sorted(secondary, key=lambda x: (x[0], x[1])):
        start, end, title = candidate[:3]
        clashes = [(i, p) for i, p in enumerate(accepted)
                   if p[0] < end and start < p[1]]
        if clashes:
            if len(clashes) == 1:
                i, existing = clashes[0]
                if existing[0] == start and existing[1] == end and normalized(existing[2]) == normalized(title):
                    if details_score(candidate) > details_score(existing):
                        accepted[i] = candidate
                        enriched += 1
                    continue
            conflicts += 1
            continue
        accepted.append(candidate)
        added += 1
    return sorted(accepted, key=lambda x: (x[0], x[1])), {
        'programmes_added': added, 'metadata_enriched': enriched,
        'overlap_conflicts': conflicts
    }


def combine_channels(primary: dict, secondary: dict) -> tuple[dict, dict]:
    """Merge schedules only when channel ID AND normalized display name agree."""
    merged = {cid: {**item, 'programmes': list(item['programmes'])}
              for cid, item in primary.items()}
    report = {'channels_added': 0, 'channels_merged': 0,
              'channels_rejected_name_conflict': 0,
              'programmes_added': 0, 'metadata_enriched': 0, 'overlap_conflicts': 0}
    for cid, item in secondary.items():
        if cid not in merged:
            merged[cid] = {**item, 'programmes': list(item['programmes'])}
            report['channels_added'] += 1
            continue
        if not normalized(item['name']) or normalized(item['name']) != normalized(merged[cid]['name']):
            report['channels_rejected_name_conflict'] += 1
            continue
        shows, stats = combine_programmes(merged[cid]['programmes'], item['programmes'])
        merged[cid]['programmes'] = shows
        report['channels_merged'] += 1
        for key, value in stats.items():
            report[key] += value
    return merged, report
