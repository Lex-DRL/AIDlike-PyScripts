# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

# noinspection SpellCheckingInspection
from urllib.parse import (
	quote as _quote,
	quote_plus as _quote_plus,
	unquote as _unquote,
	unquote_plus as _unquote_plus,
	urlsplit as _split,
	urlunsplit as _unsplit,
	parse_qs as _parse_qs,
	parse_qsl as _parse_qsl,
	urlencode as _urlencode,
	SplitResult,
)

from .__paths import _StaticDataClass


class URLs(_StaticDataClass):
	protocol = 'https'
	protocol_prefix = 'https://'
	domain = 'archiveofourown.org'
	domain_www = 'www.archiveofourown.org'

	tag_root = '/tags/'
	tag_search_root = '/tags/search'

	quote = _quote
	quote_plus = _quote_plus
	unquote = _unquote
	unquote_plus = _unquote_plus

	split_qs_dict = _parse_qs
	split_qs_list = _parse_qsl

	unsplit_qs = _urlencode

	# noinspection SpellCheckingInspection
	unsplit = _unsplit
	SplitResult = SplitResult

	# noinspection PyShadowingNames
	@classmethod
	def split(
		cls,
		url: str,
		check_domain=True,
		unquote: _t.Union[bool, int] = True,
		to_abs=True
	):
		"""
		A common URL-cleaning function, a wrapper around `urllib.urlsplit` that
		prepares the `SplitResult` in a standard format.

		:param url:
			An URL path. It can be either relative (`/path/on/site`) or absolute,
			including domain. For latter, a protocol (http/https) and 'www' can be
			included, but the output ignores it and returns whichever format is specified
			with `to_abs` argument.

		:param check_domain:
			Make sure (by asserts) that the given path is either relative or it's domain
			matches `archiveofourown.org`.

		:param unquote:
			Whether to perform url-charcodes (%20) replacement:
				False - no;
				True - yes;
				2 (int) - yes, and replace plus signs to spaces.

		:param to_abs:
			Defines the format of the output `SplitResult`:
				* True - has 'https' protocol and domain without 'www'.
				* False - relative path - has empty protocol and domain.
		"""
		if not url:
			url = ''
		assert isinstance(url, str), f"URL must be a string: {url}"
		if unquote:
			if unquote == 2:
				# noinspection PyCallByClass
				url = cls.unquote_plus(url, errors='strict')
			else:
				# noinspection PyCallByClass
				url = cls.unquote(url, errors='strict')
		url = url.lstrip('/')
		if any(
			url.startswith(x) for x in (cls.domain, cls.domain_www)
		):
			url = cls.protocol_prefix + url

		protocol, domain, path, *rest = _split(url)  # type: str
		protocol = cls.protocol

		if domain.lower().startswith('www.'):
			domain = domain[4:]
		if not domain:
			domain = cls.domain
		elif check_domain:
			assert domain.lower() == cls.domain, f'Wrong URL domain: {domain}'
			assert domain == cls.domain, f'Domain in wrong case: {domain}'

		if not to_abs:
			protocol = ''
			domain = ''

		path = '/' + path.lstrip('/')

		# noinspection PyArgumentList
		return SplitResult(protocol, domain, path, *rest)
