from datetime import datetime, timedelta, timezone
import gzip
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import addon
from epg_fusion import combine_channels, combine_programmes, normalized

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def p(hours, title='Film', description='', duration=1):
    start = NOW + timedelta(hours=hours)
    return (start, start + timedelta(hours=duration), title, description, '', '', '')


def feed(items, channel='SBS6.nl', name='SBS 6'):
    tv = ET.Element('tv')
    ch = ET.SubElement(tv, 'channel', {'id': channel})
    ET.SubElement(ch, 'display-name').text = name
    for program in items:
        show = ET.SubElement(tv, 'programme', {
            'channel': channel, 'start': program[0].strftime('%Y%m%d%H%M%S +0000'),
            'stop': program[1].strftime('%Y%m%d%H%M%S +0000')})
        ET.SubElement(show, 'title').text = program[2]
        if program[3]:
            ET.SubElement(show, 'desc').text = program[3]
    return gzip.compress(ET.tostring(tv))


class FusionTests(unittest.TestCase):
    def test_safe_normalization_removes_only_quality_tokens(self):
        self.assertEqual(normalized('SBS 6 FHD'), 'sbs6')
        self.assertEqual(normalized('SBS 6'), 'sbs6')
        self.assertNotEqual(normalized('SBS'), normalized('SBS 6'))
        self.assertNotEqual(normalized('RTL 4'), normalized('RTL 5'))

    def test_exact_id_and_equivalent_name_enrich_and_fill_gap(self):
        source = {'same.id': {'name': 'RTL 4 HD', 'programmes': [p(0), p(2)]}}
        secondary = {'same.id': {'name': 'RTL 4', 'programmes': [
            p(0, description='Genuine show description'), p(1), p(2)]}}
        result, stats = combine_channels(source, secondary)
        self.assertEqual([x[0] for x in result['same.id']['programmes']],
                         [p(0)[0], p(1)[0], p(2)[0]])
        self.assertEqual(result['same.id']['programmes'][0][3], 'Genuine show description')
        self.assertEqual(stats['programmes_added'], 1)
        self.assertEqual(stats['metadata_enriched'], 1)

    def test_enrichment_keeps_existing_genre_and_adds_missing_episode(self):
        original = (p(0)[0], p(0)[1], 'Journaal', 'Short', 'News', '', '')
        extra = (p(0)[0], p(0)[1], 'Journaal', 'A more detailed description',
                 'Entertainment', 'Daily update', 'S2 E3')
        shows, stats = combine_programmes([original], [extra])
        self.assertEqual(shows[0][3], 'A more detailed description')
        self.assertEqual(shows[0][4], 'News')
        self.assertEqual(shows[0][5], 'Daily update')
        self.assertEqual(shows[0][6], 'S2 E3')
        self.assertEqual(stats['metadata_enriched'], 1)

    def test_conflicting_title_or_schedule_is_never_overridden(self):
        shows, stats = combine_programmes([p(0, 'Nieuws')], [
            p(0, 'Sport', 'Different show'), p(0, 'Nieuws', duration=2)])
        self.assertEqual(shows, [p(0, 'Nieuws')])
        self.assertEqual(stats['overlap_conflicts'], 2)

    def test_same_id_different_country_or_name_not_merged(self):
        source = {'station': {'name': 'SBS 6', 'programmes': [p(0)]}}
        secondary = {'station': {'name': 'SBS 9', 'programmes': [p(1)]}}
        result, stats = combine_channels(source, secondary)
        self.assertEqual(result['station']['programmes'], [p(0)])
        self.assertEqual(stats['channels_rejected_name_conflict'], 1)

    def test_separate_channel_id_does_not_get_fuzzy_merged(self):
        result, stats = combine_channels(
            {'one': {'name': 'SBS 6', 'programmes': [p(0)]}},
            {'two': {'name': 'SBS 6', 'programmes': [p(1)]}})
        self.assertEqual(len(result), 2)
        self.assertEqual(stats['channels_added'], 1)

    def test_supplemental_xmltv_uses_real_description_and_future_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'published'
            primary = feed([p(0), p(2)])
            supplemental = feed([p(0, description='Extra program information'), p(1)])
            report = addon.build(out, {'NL': primary}, NOW, supplements={'NL': supplemental})
            root = ET.fromstring(gzip.decompress((out / 'epg/nl.xml.gz').read_bytes()))
            shows = root.findall('programme')
            self.assertEqual(len(shows), 3)
            self.assertEqual(shows[0].findtext('desc'), 'Extra program information')
            self.assertEqual(report['supplemental_merges']['NL']['programmes_added'], 1)
            self.assertEqual(report['supplemental_merges']['NL']['metadata_enriched'], 1)

    def test_single_pass_feed_iterator_and_streaming_gzip_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = addon.build(Path(tmp) / 'published',
                                 iter([('NL', feed([p(0)])), ('FR', feed([p(0)], 'FR1.fr', 'France 1'))]), NOW,
                                 source_status={})
            self.assertEqual(result['international_regions_available'], 2)
            self.assertEqual(result['combined_channels'], 1)
            self.assertTrue((Path(tmp) / 'published' / 'epg/fr.xml.gz').is_file())
            root = ET.fromstring(gzip.decompress(
                (Path(tmp) / 'published' / 'epg/all.xml.gz').read_bytes()))
            self.assertEqual(len(root.findall('channel')), 1)


if __name__ == '__main__':
    unittest.main()
