# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

import json as _json
from dataclasses import dataclass as _dataclass

from common import (
	CustomHash as _CustomHash,
	StaticDataClass as _StaticDataClass,
)


"""
User-Agent
	Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0
	Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0
	Mozilla/5.0 (X11; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0
	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36
	Mozilla/5.0 (Android 8.1.0; Mobile; rv:80.0) Gecko/80.0 Firefox/80.0
Upgrade-Insecure-Requests # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Upgrade-Insecure-Requests
	1

Accept
	text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8
Accept-Encoding
	gzip, deflate, br
Accept-Language
	ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3
	en-US,en;q=0.5
DNT
	1
Host
	scraped.website.org
Referer
	https://www.google.com/
Connection
	keep-alive

New Firefox (91.0):
Sec-Fetch-Dest # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-Fetch-Dest
	document
Sec-Fetch-Mode # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-Fetch-Mode
	navigate
Sec-Fetch-Site # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-Fetch-Site
	cross-site
Sec-Fetch-User # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-Fetch-User
	?1
"""


class UserAgentHeader(_t.NamedTuple):
	"""Base/boilerplate header mocking some real browser."""

	# https://user-agents.net/download?browser=firefox&platform=win8

	user_agent: _t.Optional[str]
	accept: _t.Optional[str] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
	accept_encoding: _t.Optional[str] = 'gzip, deflate, br'
	accept_language: _t.Optional[str] = 'en-US,en;q=0.5'  # 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
	upgrade_insecure: _t.Optional[int] = 1
	dnt: _t.Optional[int] = 1
	referer: _t.Optional[str] = 'https://www.google.com/'

	@property
	def header(self):
		return {
			key: val for key, val in sorted((  # sort - since Py3 keeps dict order (somewhat)
				('User-Agent', self.user_agent),
				('Upgrade-Insecure-Requests', self.upgrade_insecure),
				('DNT', self.dnt),

				('Accept', self.accept),
				('Accept-Encoding', self.accept_encoding),
				('Accept-Language', self.accept_language),

				('Referer', self.referer),
			)) if val
		}

	@classmethod
	def __os_headers(cls):
		"""
Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0
Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0
Mozilla/5.0 (X11; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0
		"""
		# https://gs.statcounter.com/os-market-share
		# https://gs.statcounter.com/os-version-market-share/windows/desktop/worldwide
		all_os_by_share = (
			()
		)

		return (
			('Windows NT 10.0; Win64; x64',),
		)

	@classmethod
	def firefox_headers(cls):
		pass


@_dataclass(eq=False, unsafe_hash=False)
class Proxy(_CustomHash):

	url: str
	active: bool = True

	@property
	def hash_id(self) -> _t.Tuple[str]:
		return (self.url, )


"""
https://spys.one/en/https-ssl-proxy/
https://free-proxy-list.net/

https://geonode.com/free-proxy-list
https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https
"""


class ProxyPool(_StaticDataClass):
	__proxies: _t.Set[Proxy]

	@classmethod
	def _load_from_geonode(cls):
		load_url = 'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https'


a0 = Proxy('aaa', False)
a1 = Proxy('aaa', True)
b0 = Proxy('bbb', False)
b1 = Proxy('bbb', True)

a0.__hash__
a0.__eq__

s = {a0, a1, b0, b1}

q = s.remove(('aaa', ))

z = ('aaa', ) in s

from pprint import pprint as pp
import requests
r = requests.get('https://google.com/')
for k, v in sorted(r.headers.items()):
	print(f'{repr(k)}: {repr(v)}')