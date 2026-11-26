import gzip
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import private_guide
from test_fusion import NOW, feed, p


class PrivateGuideTests(unittest.TestCase):
    def test_provider_ids_and_schedule_are_retained_with_other_ids(self):
        primary = feed([p(0, 'Nieuws'), p(1, 'Sport')], 'provider/1', 'TVP 1 HD')
        secondary = feed([
            p(0, 'Nieuws', 'Meer informatie'), p(1, 'Sport'), p(2, 'Film'),
            p(0.5, 'Conflict')], 'TVP1.pl', 'TVP 1')
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'pl.xml.gz'
            with patch.dict(os.environ, {'TEST_EPG_URL': 'https://provider.invalid/epg?password=test'}):
                with patch('private_guide.download', side_effect=[primary, secondary]) as download:
                    report = private_guide.generate('PL', output, ['env=TEST_EPG_URL', 'epg-ovh'], NOW)
            self.assertEqual(download.call_count, 2)
            root = ET.fromstring(gzip.decompress(output.read_bytes()))
            self.assertEqual([ch.get('id') for ch in root.findall('channel')], ['provider/1'])
            self.assertEqual([p.findtext('title') for p in root.findall('programme')],
                             ['Nieuws', 'Sport', 'Film'])
            self.assertEqual(root.findtext('programme/desc'), 'Meer informatie')
            self.assertEqual(report['sources']['epg-ovh']['matched_different_id'], 1)
            self.assertNotIn('password', str(report))

    def test_single_matching_title_or_timeshift_does_not_merge(self):
        from addon import parse

        primary, _ = parse(feed([p(0), p(1)], 'one', 'TVP 1'), NOW)
        secondary, _ = parse(feed([p(0), p(1)], 'two', 'TVP 1 HD'), NOW)
        private_guide.merge(primary, secondary)
        self.assertEqual(set(primary), {'one', 'two'})
        primary, _ = parse(feed([p(0, 'Nieuws'), p(1, 'Sport')], 'one', 'TVP 1'), NOW)
        secondary, _ = parse(feed([p(0, 'Nieuws'), p(1, 'Sport')], 'shift', 'TVP 1 +1'), NOW)
        private_guide.merge(primary, secondary)
        self.assertEqual(set(primary), {'one', 'shift'})

    def test_unavailable_regional_source_allows_other_regions_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'nl.xml.gz'
            with patch('private_guide.download', side_effect=[OSError('private URL'), feed([p(0)])]):
                report = private_guide.generate('NL', output, now=NOW)
            self.assertEqual(report['sources']['epgshare']['status'], 'unavailable')
            self.assertEqual(report['sources']['iptv-epg']['status'], 'ok')
            self.assertTrue(output.exists())

    def test_required_source_failure_keeps_previous_guide(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'pl.xml.gz'
            output.write_bytes(b'previous guide')
            with self.assertRaises(ValueError):
                private_guide.generate('PL', output, ['file=missing.xml'], NOW)
            self.assertEqual(output.read_bytes(), b'previous guide')

    def test_m3u_guide_urls_are_ordered_and_streams_are_ignored(self):
        primary = feed([p(0)], 'provider/1', 'TVP 1')
        with tempfile.TemporaryDirectory() as temp:
            playlist = Path(temp) / 'playlist.m3u'
            playlist.write_text(
                '#EXTM3U\tx-tvg-url="https://invalid/old,https://invalid/guide?token=private" '
                "url-tvg='https://invalid/old'\n#EXTINF:-1,TVP 1\nhttps://invalid/stream\n",
                encoding='utf-8-sig')
            with patch('private_guide.download', side_effect=[OSError(), primary]) as download:
                report = private_guide.generate('PL', Path(temp) / 'pl.xml.gz', [f'm3u={playlist}'], NOW)
            self.assertEqual([call.args[0] for call in download.call_args_list],
                             ['https://invalid/old', 'https://invalid/guide?token=private'])
            self.assertEqual(report['sources']['m3u-1-2']['status'], 'ok')
            self.assertNotIn('private', str(report))

    def test_country_aliases_need_corroborating_schedule(self):
        catalog = [{'id': 'SBS6.nl', 'name': 'SBS 6', 'country': 'NL', 'alt_names': []},
                   {'id': 'SBS.be', 'name': 'SBS', 'country': 'BE', 'alt_names': []}]
        primary = feed([p(0, 'Nieuws'), p(1, 'Sport')], 'provider/1', 'SBS')
        secondary = feed([p(0, 'Nieuws'), p(1, 'Sport'), p(2, 'Film')], 'SBS6.nl', 'SBS 6')
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'nl.xml.gz'
            responses = [json.dumps(catalog).encode(), primary, secondary]
            with patch('private_guide.download', side_effect=responses):
                report = private_guide.generate('NL', output, now=NOW, use_aliases=True)
            self.assertEqual(report['channels_with_schedule'], 1)
            self.assertEqual(report['programmes'], 3)
            root = ET.fromstring(gzip.decompress(output.read_bytes()))
            self.assertEqual(root.find('channel').get('id'), 'provider/1')

        from addon import parse
        guide, _ = parse(primary, NOW)
        unmatched, _ = parse(feed([p(3)], 'SBS6.nl', 'SBS 6'), NOW)
        private_guide.merge(guide, unmatched, private_guide.channel_aliases('NL', catalog))
        self.assertEqual(set(guide), {'provider/1', 'SBS6.nl'})
        catalog.append({'id': 'Other.nl', 'name': 'Other', 'country': 'NL', 'alt_names': ['SBS']})
        self.assertNotIn('sbs', private_guide.channel_aliases('NL', catalog))


if __name__ == '__main__':
    unittest.main()
