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
	tag_root_n = len(tag_root)
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

	@classmethod
	def quote_segments(
		cls,
		url_split: SplitResult,
		quote_plus=False,
	):
		"""
		Quote the urls in a smart way, keeping slashes in path but encoding
		everything else.
		"""
		assert isinstance(url_split, SplitResult), "url_split must be a SplitResult instance"
		protocol, domain, path, query, *rest = url_split

		quote_f = cls.quote_plus if quote_plus else cls.quote

		protocol, domain, *rest = (
			quote_f(x, safe='') for x in (protocol, domain, *rest)
		)
		path = quote_f(path, safe='/')
		query = quote_f(query, safe='&=')

		# noinspection PyArgumentList
		return SplitResult(protocol, domain, path, query, *rest)

	@classmethod
	def override_query(
		cls,
		url_split: SplitResult,
		keep_blank_values=True,
		strict_parsing=True,
		errors='strict',
		unquote_mode=2,
		quote_mode=2,
		query_sort_key_f: _t.Optional[_t.Callable[[_t.Tuple[int, str, _t.Any]], _t.Any]] = None,
		**kwargs
	):
		"""
		Return a copy of url_split, with modified query.

		When no kwargs provided, this can be used to just clean up the query part of URL.

		Unquote is (optionally) done before parsing query, quote - after.

		If `query_sort_key_f` function provided, a sorting is performed.
		This function takes a single argument as a tuple of:
			* int, the original index of argument
			* str - query key
			* query value
		"""

		assert isinstance(url_split, SplitResult), "url_split must be a SplitResult instance"
		protocol, domain, path, query_str, *rest = url_split

		# noinspection PyUnusedLocal,PyShadowingNames
		def dummy_quote(string: _t.AnyStr, *args, **kwargs):
			return string

		quote_f = {
			1: cls.quote,
			2: cls.quote_plus,
		}.get(quote_mode, dummy_quote)
		unquote_f = {
			1: cls.unquote,
			2: cls.unquote_plus,
		}.get(unquote_mode, dummy_quote)

		query_str = unquote_f(query_str.replace('&amp;', '&'), errors=errors)

		query_list = cls.split_qs_list(
			query_str, keep_blank_values=keep_blank_values, strict_parsing=strict_parsing,
			errors=errors,
		)
		# replace/remove existing keys:
		query_list: _t.List[_t.Tuple[_t.AnyStr, _t.AnyStr]] = [
			(key, value) for key, value, original in (
				(k, kwargs[k], False) if k in kwargs else (k, v, True)
				for k, v in query_list
			) if original or value is not None  # remove overrides with key=None
		]
		# add new keys:
		present_keys = {k for k, v in query_list}
		for k, v in kwargs.items():
			if v is None or k in present_keys:
				continue
			query_list.append((k, v))

		if callable(query_sort_key_f):
			query_list = [
				(key, val) for idx, key, val in sorted(
					((i, k, v) for i, (k, v) in enumerate(query_list)),
					key=query_sort_key_f
				)
			]

		# compile query back:
		# noinspection PyCallByClass
		query_str = cls.unsplit_qs(
			query_list, doseq=False, errors=errors, quote_via=quote_f
		)

		# noinspection PyArgumentList
		return SplitResult(protocol, domain, path, query_str, *rest)
