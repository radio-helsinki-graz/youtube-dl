# coding: utf-8
from __future__ import unicode_literals

import datetime
import os

from .common import InfoExtractor
from ..utils import (
    clean_html,
    ExtractorError,
    RegexNotFoundError,
    UnavailableVideoError,
    update_url_query,
)

class CBAIE(InfoExtractor):
    IE_NAME = 'cba'
    IE_DESC = 'cultural broadcasting archive'
    _VALID_URL = r'https?://(?:www\.)?cba\.fro\.at/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://cba.fro.at/320619',
        'md5': 'e40379688fcc5e95d6d8a482bb665b02',
        'info_dict': {
            'id': '320619',
            'ext': 'mp3',
            'title': 'Radio Netwatcher Classics vom 15.7.2016 – Peter Pilz, Sicherheitssprecher Grüne über die nationale Entwicklung zum Überwachungsstaat',
            'url': 'https://cba.fro.at/wp-content/uploads/radio_netwatcher/netwatcher-20160715.mp3',
        }
    }
    _FORMATS = {
        'audio/ogg': {'id': '1', 'ext': 'ogg', 'preference': 100},
        'audio/mpeg': {'id': '2', 'ext': 'mp3', 'preference': 50}
    }
    _API_KEY = None

    def __init__(self, *args, **kwargs):
        try:
            self._API_KEY = os.environ["CBA_API_KEY"]
        except KeyError:
            pass

    def _parse_bool(self, bool_str):
        return bool_str.lower() in ("yes", "true", "t", "1")

    def _parse_cba_datetime(self, date_str):
        if date_str is None:
            return None

        try:
            date_format = '%a, %d %b %Y %H:%M:%S'
            return datetime.datetime.strptime(date_str, date_format)
        except ValueError:
            try:
                date_format = '%a, %d %b %Y'
                return datetime.datetime.strptime(date_str, date_format)
            except ValueError:
                pass


    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        seriesrss = self._html_search_regex(r'<a href="(.+?/seriesrss/[0-9]+?)">', webpage, 'Link to Series-RSS')
        if not seriesrss:
            RegexNotFoundError()

        title = ''
        description = ''
        productionDate = None
        broadcastDate = None
        containsCopyright = False
        formats = []

        ns = {'cba': 'https://cba.fro.at',
              'content': 'http://purl.org/rss/1.0/modules/content/'}

        api_key_str = ""
        if self._API_KEY:
            api_key_str =  " (using API_KEY '%s')" % self._API_KEY
            seriesrss = update_url_query(seriesrss, {'c': self._API_KEY})

        rss = self._download_xml(seriesrss, video_id, 'Downloading Series-RSS%s' % api_key_str)
        for it in rss.findall('./channel/item'):
            if it.find('link').text == url:
                title = clean_html(it.find('title').text)
                if it.find('content:encoded', ns) is not None:
                    description = it.find('content:encoded', ns).text
                else:
                    description = clean_html(it.find('description').text)

                productionDate = self._parse_cba_datetime(it.find("cba:productionDate", ns).text)
                if it.find("cba:broadcastDate", ns) is not None:
                    broadcastDate = self._parse_cba_datetime(it.find("cba:broadcastDate", ns).text)
                if it.find("cba:containsCopyright", ns) is not None:
                    containsCopyright = self._parse_bool(it.find("cba:containsCopyright", ns).text)

                enclosures = it.findall('./enclosure')
                if len(enclosures) == 0:
                    if containsCopyright:
                        raise UnavailableVideoError('Unable to find file due to copyright restrictions!')
                    else:
                        raise ExtractorError('RSS feed entry has no enclosures but <cba:containsCopyright> is false!')
                else:
                    for enclosure in enclosures:
                        try:
                            formats.append({
                                'url': enclosure.attrib.get('url'),
                                'format': enclosure.attrib.get('type'),
                                'format_id': self._FORMATS[enclosure.attrib.get('type')]['id'],
                                'preference': self._FORMATS[enclosure.attrib.get('type')]['preference'],
                                'filzesize': enclosure.attrib.get('length'),
                            })
                        except KeyError:
                            pass

                break

        if len(formats) == 0:
            raise ExtractorError('Unable to find CBA entry in RSS feed')

        self._sort_formats(formats)

        productionDateIso = None
        broadcastDateIso = None
        if productionDate:
            productionDateIso = productionDate.isoformat()
        if broadcastDate:
            broadcastDateIso = broadcastDate.isoformat()

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'series-rss': seriesrss,
            'productionDate': productionDateIso,
            'broadcastDate': broadcastDateIso,
            'containsCopyright': containsCopyright,
            'formats': formats,
        }
