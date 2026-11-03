from datetime import datetime, timedelta, timezone
import gzip
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

import addon

NOW = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)


def feed(count=1):
    root = ET.Element('tv')
    for i in range(count):
        cid = 'station/' + str(i) + '.nl'
        ch = ET.SubElement(root, 'channel', id=cid)
        ET.SubElement(ch, 'display-name').text = 'Station ' + str(i)
        ET.SubElement(ch, 'icon', src='https://secret.invalid/logo?password=do-not-publish')
        for hour in (-2, 0, 1, 24):
            start = NOW + timedelta(hours=hour)
            end = start + timedelta(hours=1)
            p = ET.SubElement(root, 'programme', channel=cid,
                              start=start.strftime('%Y%m%d%H%M%S +0000'),
                              stop=end.strftime('%Y%m%d%H%M%S +0000'))
            ET.SubElement(p, 'title').text = 'Programme ' + str(hour)
            ET.SubElement(p, 'desc').text = 'private provider URL must not pass through'
    return ET.tostring(root)


class AddonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'public'

    def read(self, path):
        return json.loads((self.output / path).read_text(encoding='utf-8'))

    def test_manifest_and_nuvio_compatible_catalog(self):
        report = addon.build(self.output, {'NL': gzip.compress(feed())}, NOW)
        manifest = self.read('manifest.json')
        self.assertEqual(manifest['resources'], ['catalog', 'meta', 'stream'])
        self.assertTrue(manifest['behaviorHints']['epgProvider'])
        self.assertEqual(manifest['catalogs'][0]['id'], 'nl')
        self.assertEqual(report['regions']['NL']['channels_with_schedule'], 1)
        catalog = self.read('catalog/tv/nl.json')['metas']
        self.assertEqual(len(catalog), 1)
        self.assertIn('Programme 0', catalog[0]['description'])
        cid = catalog[0]['id']
        self.assertNotIn('/', cid)
        meta = self.read('meta/tv/' + cid + '.json')['meta']
        self.assertEqual(len(meta['videos']), 3)
        self.assertEqual(meta['videos'][0]['startTime'], '2026-11-03T10:00:00Z')
        self.assertEqual(self.read('stream/tv/' + cid + '.json'), {'streams': []})

    def test_no_remote_urls_or_provider_extensions_leak(self):
        addon.build(self.output, {'NL': feed()}, NOW)
        raw = b'\n'.join(p.read_bytes() for p in self.output.rglob('*') if p.is_file())
        self.assertNotIn(b'secret.invalid', raw)
        self.assertNotIn(b'do-not-publish', raw)
        xml = gzip.decompress((self.output / 'epg/nl.xml.gz').read_bytes())
        self.assertNotIn(b'private provider', xml)
        root = ET.fromstring(xml)
        self.assertEqual(root.find('channel').get('id'), 'station/0.nl')
        self.assertEqual(len(root.findall('programme')), 3)

    def test_short_page_ends_at_actual_count_and_date_orders_work(self):
        addon.build(self.output, {'NL': feed(101)}, NOW)
        self.assertEqual(len(self.read('catalog/tv/nl.json')['metas']), 100)
        self.assertEqual(len(self.read('catalog/tv/nl/skip=100.json')['metas']), 1)
        self.assertEqual(self.read('catalog/tv/nl/skip=101.json')['metas'], [])
        left = self.read('catalog/tv/nl/date=2026-11-03&skip=100.json')
        right = self.read('catalog/tv/nl/skip=100&date=2026-11-03.json')
        self.assertEqual(left, right)
        self.assertEqual(len(left['metasDetailed'][0]['videos']), 2)
        self.assertEqual(self.read('catalog/tv/nl/date=2026-11-03&skip=101.json')['metasDetailed'], [])

    def test_country_ids_do_not_collide(self):
        self.assertNotEqual(addon.channel_id('NL', 'same'), addon.channel_id('BE', 'same'))
        self.assertEqual(addon.channel_id('NL', 'same'), addon.channel_id('NL', 'same'))

    def test_expired_invalid_and_overlapping_programmes_are_not_kept(self):
        root = ET.fromstring(feed())
        duplicate = ET.fromstring(ET.tostring(root.findall('programme')[1]))
        root.append(duplicate)
        bad = ET.SubElement(root, 'programme', channel='station/0.nl', start='invalid', stop='invalid')
        ET.SubElement(bad, 'title').text = 'Bad'
        parsed, report = addon.parse(ET.tostring(root), NOW)
        self.assertEqual(len(parsed['station/0.nl']['programmes']), 3)
        self.assertEqual(report['invalid_programmes'], 1)

    def test_unsafe_and_oversized_xml_are_rejected(self):
        for raw in (b'<!DOCTYPE tv [<!ENTITY x "bad">]><tv/>', b'<tv>\x00</tv>', b'<other/>'):
            with self.assertRaises(ValueError): addon.parse(raw, NOW)
        with patch.object(addon, 'MAX_XML', 20):
            with self.assertRaises(ValueError): addon.parse(gzip.compress(feed()), NOW)

    def test_timezone_conversion_and_missing_offset(self):
        self.assertEqual(addon.timestamp('202611031100 +0100'), NOW)
        with self.assertRaises(ValueError): addon.timestamp('20261103110000')

    def test_standard_xmltv_dtd_is_ignored_without_network_resolution(self):
        raw = b'<!DOCTYPE tv SYSTEM "xmltv.dtd">' + feed()
        parsed, _ = addon.parse(raw, NOW)
        self.assertEqual(len(parsed), 1)
        with self.assertRaises(ValueError):
            addon.parse(b'<!DOCTYPE tv SYSTEM "https://example.invalid/remote.dtd">' + feed(), NOW)

    def test_timezone_database_failure_is_labelled_utc(self):
        with patch.object(addon, 'ZoneInfo', side_effect=addon.ZoneInfoNotFoundError('missing')):
            result = addon.description('NL', [(NOW, NOW + timedelta(hours=1), 'Test')], NOW)
        self.assertIn('Tijden hieronder: UTC.', result)
        self.assertIn('10:00', result)

    def test_combined_guide_deduplicates_ids_without_changing_channel_identity(self):
        report = addon.build(self.output, {'NL': feed(), 'BE': feed()}, NOW)
        root = ET.fromstring(gzip.decompress((self.output / 'epg/all.xml.gz').read_bytes()))
        self.assertEqual(len(root.findall('channel')), 1)
        self.assertEqual(report['duplicate_xmltv_ids_first_source_wins'], 1)

    def test_all_source_failure_does_not_create_published_output(self):
        with patch.object(addon, 'fetch', side_effect=ValueError('do not log secret URL')):
            with self.assertRaises(ValueError): addon.generate(self.output, NOW)
        self.assertFalse((self.output / 'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
