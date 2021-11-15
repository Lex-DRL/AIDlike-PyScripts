# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

import re as _re
import json as _json
from pathlib import Path
from collections import defaultdict

from common import (
	root_dir as _root_dir,
	StaticDataClass as _StaticDataClass,
)


_re_ua = _re.compile(
	'\\s*(?P<prefix>[^(]*)'     # Mozilla/5.0
	'\\s*\\('                   # (
	'(?P<os>[^;]+);\\s*'                      # Windows NT 10.0;
	'(?P<platform>[^;]+(?:;[^;]+)??)'         # Win64 [; x64]
	'(?:\\s*;\\s*rv\\s*:\\s*(?P<rv>[^)]+))?'  # [; rv:81.0]
	'\\)\\s*'                   # )
	'(?P<browser>.+)',  # Gecko/20100101 Firefox/91.0

	flags=_re.IGNORECASE
)
_re_ff_browser = _re.compile(
	'Gecko\\s*/\\s*(?P<gecko>[a-zA-Z_0-9.-]+)\\s*'
	'.*?'
	'Firefox\\s*/\\s*(?P<firefox>[a-zA-Z_0-9.-]+)',

	flags=_re.IGNORECASE
)
_empty_str = ''


class FirefoxBrowser(_t.NamedTuple):
	gecko: str = _empty_str
	firefox: str = _empty_str

	@classmethod
	def from_string(cls, browser_str: str):
		m = _re_ff_browser.match(browser_str.strip())
		if not m:
			return None

		kwargs = m.groupdict()
		if not kwargs:
			return None
		kwargs = {
			k: v for k, v in kwargs.items()
			if v
		}
		return FirefoxBrowser(**kwargs)


class UserAgent(_t.NamedTuple):
	"""
	https://user-agents.net/download?browser=firefox&platform=win8

	FireFox:
		Win10/91:
			Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0
		Win8.1/89:
			Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0
		Win7/87:
			Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0
		Linux:
			Mozilla/5.0 (X11; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0
		Android:
			Mozilla/5.0 (Android 8.1.0; Mobile; rv:80.0) Gecko/80.0 Firefox/80.0
	Chrome:
		Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36
	"""

	prefix: str = _empty_str
	os: str = _empty_str
	platform: str = _empty_str
	rv: str = _empty_str
	browser: str = _empty_str

	@classmethod
	def from_string(cls, ua_str: str):
		m = _re_ua.match(ua_str.strip())
		if not m:
			return None

		kwargs = m.groupdict()
		if not kwargs:
			return None
		kwargs = {
			k: v for k, v in kwargs.items()
			if v
		}
		return UserAgent(**kwargs)

	def __str__(self):
		os_platform = [
			x for x in map(
				str.strip, (self.os, self.platform)
			) if x
		]
		rv = self.rv.strip()
		if rv:
			os_platform.append(f'rv:{rv}')
		os_platform = '; '.join(x for x in (self.os, self.platform))
		return f'{self.prefix.strip()} ({"; ".join(os_platform)}) {self.browser.strip()}'.strip()


def __load_user_agents_from_file(file_path: Path):
	with file_path.open('rt', encoding='UTF-8') as f:
		ua_strs: _t.List[str] = _json.load(f)

	parsed: _t.Dict[str, _t.Optional[UserAgent]] = {
		ua_str: UserAgent.from_string(ua_str)
		for ua_str in set(ua_strs)
	}
	ok: _t.List[UserAgent] = list()
	not_parsed: _t.List[str] = list()
	for ua_str, ua_obj in parsed.items():
		if ua_obj:
			ok.append(ua_obj)
		else:
			not_parsed.append(ua_str)

	return ok, not_parsed


_dumps_dir = _root_dir / 'user_agents'


def __analyze_ff_browsers(file_path: Path):
	ok_agents, not_parsed = __load_user_agents_from_file(file_path)
	n_ok = len(ok_agents)
	n_not = len(not_parsed)
	print(f'Firefox browsers: {n_ok}, not parsed: {n_not} ({100*n_not / n_ok:.2f}%)')

	if 0 < n_not < 50:
		print('\nNot parsed:')
		for s in sorted(not_parsed):
			print(f'\t{s}')

	all_browsers: _t.Dict[str, _t.Optional[FirefoxBrowser]] = {
		x.browser: FirefoxBrowser.from_string(x.browser)
		for x in ok_agents
	}
	erratic_browsers = [k for k, v in all_browsers.items() if not v]
	all_browsers = {k: v for k, v in all_browsers.items() if v}

	if 0 < len(erratic_browsers) < 50:
		print('\nUnable to parse FF browsers:')
		for b_str in erratic_browsers:
			print(f'\t{b_str}')

	ffs_by_gecko: _t.Dict[str, _t.List[str]] = defaultdict(list)
	for b in all_browsers.values():
		ffs_by_gecko[b.gecko.lower()].append(b.firefox)

	matching_geckos: _t.Dict[str, str] = dict()
	for gecko, ffs in sorted(ffs_by_gecko.items()):
		ffs = set(ffs)
		if len(ffs) > 1:
			ffs_by_gecko[gecko] = list(ffs)
			continue
		ffs_by_gecko.pop(gecko)
		ff: str = ffs.pop()
		matching_geckos[gecko] = _empty_str if ff.lower() == gecko.lower() else ff

	if matching_geckos:
		print('\nGecko with exact match to FF:')
		for gecko, ff in sorted(matching_geckos.items()):
			if ff:
				print(f'\t{gecko} -> {ff}')
				continue
			print(f'\t{gecko}')

	if ffs_by_gecko:
		print('\nGecko matching multiple FF versions:')
		for gecko, ffs in sorted(ffs_by_gecko.items()):
			print(f'\tGecko {gecko}:')
			for ff in sorted(set(ffs)):
				print(f'\t\t{ff}')

	platform_by_os: _t.Dict[str, _t.Set[str]] = defaultdict(set)
	for ua in ok_agents:
		platform_by_os[ua.os].add(ua.platform)
	if platform_by_os:
		print('\n\n\nOperating systems:')
		for os, platforms in sorted(platform_by_os.items()):
			if len(platforms) < 2:
				pf = tuple(platforms)[0]
				os_pf = '; '.join(x for x in (os, pf) if x)
				print(f'\t{os_pf}')
				continue

			# multiple platforms per single os
			print(f'\t{os}:')
			for pf in sorted(platforms):
				print(f'\t\t{pf}:')



if __name__ == '__main__':
	__analyze_ff_browsers(_dumps_dir / 'user-agents_firefox_android.json')
