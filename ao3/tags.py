# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import errno
from enum import Enum
from itertools import chain
from collections import OrderedDict
from dataclasses import dataclass as _dataclass
from datetime import (
	datetime as dt,
	timezone as tz,
)
from json import (
	dumps as _json_dumps,
	loads as _json_loads,
)

import requests
# noinspection PyProtectedMember
from bs4 import (
	BeautifulSoup,
	Tag as _bsTag
)

from common import (
	CustomHash as _CustomHash,
	StaticDataClass as _StaticDataClass,
)
from scraper._wip_async_request import get_pages as _get_pages_async
from .__url import URLs
from .__paths import Paths

from drl_typing import *


parser = 'lxml'


class TagType(Enum):
	Fandom = 0
	Character = 1
	Relationship = 2
	Freeform = 3

	Unsorted = 7

	def __repr__(self):
		return "%s.%s" % (self.__class__.__name__, self.name)


type_parse_map = {
	'Fandom': TagType.Fandom,
	'Character': TagType.Character,
	'Relationship': TagType.Relationship,
	'Freeform': TagType.Freeform,
	'UnsortedTag': TagType.Unsorted,
}


def _f_none():
	return None


_empty_str = ''  # to use the same string object across different tags

_defaults_none = (None, _f_none)
_defaults_str = (_empty_str, str)
# all the tags need to ALWAYS have their own sets for refs, so even though
# the default VALUE is None, default FACTORY returns a new set:
_defaults_ref = (None, set)
_tag_defaults = OrderedDict([
	# default value, default factory
	('type', _defaults_none),
	('name', _defaults_str),
	('url_token', _defaults_str),
	('canonical', (False, lambda: False)),
	('usages', (-1, lambda: -1)),
	('date', _defaults_none),
	('synonyms', _defaults_ref),
	('parents', _defaults_ref),
	('children', _defaults_ref),
	('subtags', _defaults_ref),
	('metatags', _defaults_ref),
])
_t_tag_ref = _set_str
_unknown_tag_usage: int = _tag_defaults['usages'][0]  # default <usage> value
_type = type
NoneType = type(None)


class Tag(_NT, _CustomHash):
	"""
	An AO3's tag is uniquely identified with it's name and (possibly) url token.
	idk if there can be multiple tags with identical names but their URLs are
	unique for sure.

	So, by it's nature, tag is immutable, therefore this class is typed NamedTuple,
	despite some ot it's "additional data" fields might be changed at runtime.
	Besides, there will be a ton of tags in DB, so memory efficiency is important, too.

	**WARNING:**
	----------
	Use `new_instance()` class method to create new instances, not just `Tag()`.
	This is the only way to make a tag instance properly initialized.
	If you don't, fields may contain whatever you put there, without any
	checks/cleanup (and therefore, data won't be in an expected format).
	Unfortunately, NamedTuple doesn't provide a way to override a built-in constructor.

	Equality check and hashing
	----------
	For equality check and hashing, only **name** and **url_token** are used.
	Beware about it. Since, if you just make a full slice, the newly created
	regular tuple is already not equal to the tag instance.

	Therefore:
		* `(name, url_token) == tag_instance`
		* `(type, name, url_token) != tag_instance`
		* `(type, name, url_token, canonical, usages, date) != tag_instance`

	Fields
	----------
	*type:*
		First, but optional (not identifying) field. One of:
			- `TagType` enum member if some of known tag types.
			- A regular string if somehow there's no such tag type in the enum.
			- None if not set.
	**name**:
		A (probably) unique non-empty string.
	**url_token**:
		Unique part of tag's url. I.e.: `/tags/{url_token}`. To save on characters, it's
		stored as just '/' if it's equal to name.
	*canonical:*
		Bool indicating if tag is canonical. None if not set.
	*usages:*
		How many works are tagged with this one. -1 if not set.
	*date:*
		The last time this tag entry populated it's properties from the actual
		tag page. It's used to cache tags locally but update them from time to time.
	"""
	type: _u[None, TagType, str]
	name: str

	url_token: str = _tag_defaults['url_token'][0]

	canonical: _o_b = _tag_defaults['canonical'][0]
	usages: int = _unknown_tag_usage
	date: _o[dt] = _tag_defaults['date'][0]

	synonyms: _t_tag_ref = _tag_defaults['synonyms'][0]
	parents: _t_tag_ref = _tag_defaults['parents'][0]
	children: _t_tag_ref = _tag_defaults['children'][0]
	subtags: _t_tag_ref = _tag_defaults['subtags'][0]
	metatags: _t_tag_ref = _tag_defaults['metatags'][0]

	@property
	def hash_id(self):
		return self.name, self.url_token

	@classmethod
	def _clean_date(cls, calling_method: str, date: _o[dt], name: str = None):
		"""
		Part of `_clean_args()` that checks only date argument
		(it might be needed to check it separately).
		"""
		tag_part = cls.__name__ if name is None else f'for tag <{name}>'
		assert isinstance(date, (NoneType, dt)), (
			f'Wrong date {tag_part}.{calling_method}(): {repr(date)}'
		)
		date: _o[dt] = date
		return date

	# noinspection PyShadowingBuiltins
	@classmethod
	def _clean_args(
		cls,
		calling_method: str,
		*args,
		**kwargs
	):
		"""
		Perform check on input arguments and auto-clean them if possible.

		If '/' is provided as **url_token**, it's value is taken from name.
		"""

		def _args_gen(args_seq: _i, kwargs_dict: dict):
			"""Combine args and kwargs to just a sequence of positional args."""
			for arg_nm, (default_val, default_f) in _tag_defaults.items():
				if args_seq:
					# if we're still iterating over positional args, they're priority:
					arg, *args_seq = args_seq
					yield arg
					continue
				if arg_nm in kwargs_dict:
					# ... then use a kwarg if given:
					yield kwargs_dict[arg_nm]
				# ... otherwise, return a default:
				yield default_f()

		# noinspection PyShadowingNames
		def _clean_url_token(url_token: str, name: str):
			if url_token == _TagDumpConfig.token_match_name_indicator:
				url_token = name

			# url_token = 'https://archiveofourown.org/tags/Admiral%20Anderson'
			# url_token = 'https://archiveofourown.org/tags/Background+Male+Shepard'
			# url_token = '/tags/Mass%20Effect%20Trilogy'
			# url_token = 'Mass Effect Trilogy'
			# url_token = 'Mass Effect Trilogy/works'

			if URLs.tag_url_re_match(url_token):
				# the string matches tag-URL pattern, let's clean it:

				# '+' inside path isn't treated by AO3 the same as %20. So unquote=1:
				url_token: str = URLs.split(url_token, unquote=1, to_abs=False).path

			# from here, url_token is either '/tags/token_string' or just '/token_string'.
			# The first one is if a proper url provided - either abs or rel.
			# the second one is if just a pure token itself was given.
			# We need to detect which it is and check each accordingly:
			if url_token.startswith(URLs.tag_root):
				# the actual URL was given.
				url_token = url_token[URLs.tag_root_n:].strip('/')
				# ... and in case there was something like '/tags/token_string/works':
				url_token = url_token.split('/')[0]
			else:
				# a pure token name was given.
				url_token = url_token.strip('/')
			# but if so, it shouldn't contain any slashes, which we assert below.

			return url_token

		# noinspection PyShadowingNames
		def _clean_ref(val, name: str, ref_name: str) -> _t_tag_ref:
			"""Prepare ref-field value to be passed to the constructor."""
			def _ensure_ref_item_type(item):
				assert isinstance(item, str) and item, (
					f'Wrong {ref_name} item passed for tag <{name}>.{calling_method}(): {repr(item)}'
				)
				return item

			default_f = _defaults_ref[1]
			if not val:
				return default_f()
			if isinstance(val, str):
				val = [val]

			return default_f(
				_ensure_ref_item_type(x) for x in val
			)

		(
			type, name, url_token,
			canonical, usages, date,
			synonyms, parents, children, subtags, metatags,
		) = _args_gen(args, kwargs)

		assert name and isinstance(name, str), (
			f'Invalid tag name passed to {cls.__name__}.{calling_method}(): {repr(name)}'
		)

		url_token = _clean_url_token(url_token, name)
		assert isinstance(url_token, str) and (
			_TagDumpConfig.token_match_name_indicator not in url_token
		), (
			f'Wrong URL for tag <{name}>.{calling_method}(): {repr(url_token)}'
		)

		if canonical is not None:
			canonical = bool(canonical)

		if usages is None:
			usages = _unknown_tag_usage

		assert isinstance(type, (NoneType, TagType, str)), (
			f'Wrong type for tag <{name}>.{calling_method}(): {repr(type)}'
		)
		assert isinstance(canonical, (NoneType, bool)), (
			f'Wrong canonical state for tag <{name}>.{calling_method}(): {repr(canonical)}'
		)
		assert isinstance(usages, int), (
			f'Wrong usages for tag <{name}>.{calling_method}(): {repr(usages)}'
		)

		# use the same object for empty strings to further reduce memory footprint:
		type, url_token = (
			_empty_str if (isinstance(x, str) and x == _empty_str) else x
			for x in (type, url_token)
		)
		# ... or use the same object for name and token if they're identical:
		if url_token == name:
			url_token = name

		type: _u[None, TagType, str] = type
		canonical: _o_b = canonical
		date: _o[dt] = cls._clean_date(calling_method, date, name)
		if date is None and usages > -1:
			date = dt.now()

		synonyms, parents, children, subtags, metatags = (
			_clean_ref(val, name, ref_name)
			for val, ref_name in (
				(synonyms, 'synonyms'),
				(parents, 'parents'),
				(children, 'children'),
				(subtags, 'subtags'),
				(metatags, 'metatags'),
			)
		)
		synonyms: _t_tag_ref = synonyms
		parents: _t_tag_ref = parents
		children: _t_tag_ref = children
		subtags: _t_tag_ref = subtags
		metatags: _t_tag_ref = metatags

		return (
			type, name, url_token,
			canonical, usages, date,
			synonyms, parents, children, subtags, metatags,
		)

	# noinspection PyShadowingBuiltins
	@classmethod
	def new_instance(
		cls,
		# let's just repeat all the args here explicitly, for IDE hints:

		type: _u[None, TagType, str],
		name: str,
		url_token: _o_str = None,

		canonical: _o_b = False,
		usages: _o[int] = _unknown_tag_usage,
		date: _o[dt] = None,

		synonyms: _t_tag_ref = None,
		parents: _t_tag_ref = None,
		children: _t_tag_ref = None,
		subtags: _t_tag_ref = None,
		metatags: _t_tag_ref = None,
	):
		"""
		Use this factory instead of just `Tag()` constructor, because it ensures
		proper initialization, turning the fields' values to an expected format.
		"""
		(
			type, name, url_token, canonical, usages, date,
			synonyms, parents, children, subtags, metatags,
		) = cls._clean_args(
			'new_instance',
			type, name, url_token, canonical, usages, date,
			synonyms, parents, children, subtags, metatags,
		)

		# put into kwargs only those that override the default values:
		required_args = {'type', 'name'}
		kwargs = {
			arg_name: arg_val for arg_val, (arg_name, (def_val, def_factory)) in zip(
				(
					type, name, url_token, canonical, usages, date,
					synonyms, parents, children, subtags, metatags,
				),
				_tag_defaults.items()
			) if arg_name not in required_args and arg_val != def_val
		}

		return cls(
			type, name, **kwargs
		)

	@classmethod
	def build_from_li(cls, tag_li: _bsTag):
		"""Build a tag object from tag's <li> html on search page."""

		# <li>
		# <span class="canonical">
		# 	Character:
		# 	<a class="tag" href="/tags/Male%20Shepard%20(Mass%20Effect)">
		# 		Male Shepard (Mass Effect)
		# 	</a>
		# 	‎(2806)
		# </span>
		# </li>
		a = tag_li.find('a', class_='tag')
		span = a.find_parent('span')
		span_attrs = span.attrs

		canonical = (
			bool(span_attrs)
			and 'class' in span_attrs
			and 'canonical' in span_attrs['class']
		)

		type_str = span.find(text=True).strip().rstrip(':')
		tag_type = type_parse_map.get(type_str, str(type_str))

		return cls.new_instance(
			tag_type, a.text, canonical=canonical, url_token=a.get('href')
		)

	@classmethod
	def date_str(cls, date: _o[dt]):
		clean_date = cls._clean_date('date_str', date)
		if clean_date is None:
			return _empty_str
		return clean_date.strftime(_TagDumpConfig.date_format)

	@classmethod
	def date_from_str(cls, date_str: _o_str, in_timezone=None):
		if not date_str:
			return None
		return dt.strptime(date_str, _TagDumpConfig.date_format).astimezone(in_timezone)

	@classmethod
	def _reorder_fields_to_dump(
		cls, items: _i[_tpl[str, str]]
	) -> _tpl[_tpl[str, str], ...]:
		"""Reorder tag elements from tuple to dumped order."""
		# noinspection PyShadowingBuiltins
		type, name, url_token, canonical, usages, date, *refs = items

		optional_fields = (
			(dump_id, val) for dump_id, val in (
				type, canonical, usages, date, *refs
			) if val
		)

		return (name, url_token, *optional_fields)

	# noinspection PyShadowingBuiltins
	def dumps(self) -> _tpl_str:
		"""
		Dump tag object to a string representation for saving to a file.

		No trailing newline characters.
		"""

		type, name, url_token, canonical, usages, date, *refs = self._clean_args(
			'dumps', *self,
		)

		if url_token == name:
			url_token = _TagDumpConfig.token_match_name_indicator

		dump_maps = _TagDumpConfig.dump_map

		if not type:
			type = _empty_str
		if isinstance(type, TagType):
			# noinspection PyTypeChecker
			type: str = dump_maps.type[type]
		assert isinstance(type, str)

		# noinspection PyUnresolvedReferences
		canonical_s: str = dump_maps.canonical[canonical]

		if usages is None or usages < 0:
			usages = -1
		usages_s: str = _empty_str if usages < 0 else str(usages)

		date_s = _empty_str if date is None else self.date_str(date.astimezone(tz=tz.utc))

		def check_ref_item(item, ref_name: str):
			if not item:
				return _empty_str
			assert isinstance(item, str), (
				f'Wrong {ref_name} item found at <{name}> tag dump: {repr(item)}'
			)
			return item

		def dump_ref(ref_set: _t_tag_ref, ref_name: str):
			if not ref_set:
				return _empty_str
			sorted_items = sorted(
				check_ref_item(x, ref_name) for x in ref_set
				if x
			)
			return _json_dumps(sorted_items, ensure_ascii=False)

		refs_s = [
			dump_ref(ref_set, ref_name) for ref_set, ref_name in zip(
				refs,
				('synonyms', 'parents', 'children', 'subtags', 'metatags',),
			)
		]

		id_val_pairs = self._reorder_fields_to_dump(zip(
			_TagDumpConfig.dump_id,
			(type, name, url_token, canonical_s, usages_s, date_s, *refs_s),
		))
		return tuple(
			id + val for id, val in id_val_pairs
		)

	def sorting_key(self):
		"""A key for tags sort."""

		# noinspection PyShadowingBuiltins
		def type_string(type):
			if type is None:
				return _empty_str
			if isinstance(type, str):
				return type
			assert isinstance(type, TagType)
			return f'{type.value}_{type.name}'

		def date_key(date: _o[dt]):
			if date is None:
				date = _TagDumpConfig.zero_day
			return _TagDumpConfig.zero_day - date

		return (
			not self.canonical, -self.usages, type_string(self.type),
			self.name, self.url_token, date_key(self.date)
		)


# noinspection PyTypeChecker
class _TagDumpConfig(_StaticDataClass):
	"""Constants related to dumped tag format."""

	# to sort tags by date, we need to subtract it from SOME date, so let's use smth round:
	zero_day = dt(2020, 1, 1, 0, 0, 0, 0, None)

	date_format: str = '%Y.%m.%d-%H:%M:%S|%Z'

	# A char that can't possibly be inside url token, we use it to indicate that
	# token url is exactly the same as name, to save on dump size (and mem footprint):
	token_match_name_indicator = '/'

	dump_id = Tag(
		type='-Tp:', name='-Tag:', url_token='-URL:',
		canonical='-Canon:', usages='-Use:', date='-Dt:',

		synonyms='\t=>Syn:',
		parents='\t=>Parent:',
		children='\t=>Child:',
		subtags='\t=>Sub:',
		metatags='\t=>Meta:',
	)
	dump_map = Tag(
		type={
			TagType.Fandom: 'Fandom',
			TagType.Character: 'Character',
			TagType.Relationship: 'Relationship',
			TagType.Freeform: 'Freeform',
			TagType.Unsorted: 'UnsortedTag',
		},
		name=None,
		url_token=None,
		canonical={
			None: _empty_str,
			True: '+',
			False: '-',
		},
	)


class TagSet(_set[Tag]):

	name: str = _empty_str

	def __init__(self, *args, name: str = _empty_str):
		super(TagSet, self).__init__(*args)
		if name:
			self.name = name

	def __repr__(self):
		res = super(TagSet, self).__repr__()
		if self.name:
			res = res.replace('(', f'({repr(self.name)}: ', 1)
		return res

	def dumps(self, separator_line=_empty_str):
		"""
		Generator iterating over all the lines in a combined dump
		of all the tags in this set.
		"""

		def sort_key(x: Tag):
			return x.sorting_key()

		sorted_tags: _t.Iterator[Tag] = iter(sorted(self, key=sort_key))
		try:
			first_tag = next(sorted_tags)
		except StopIteration:
			return

		for line in first_tag.dumps():
			yield line

		for tag in sorted_tags:
			yield separator_line
			for line in tag.dumps():
				yield line


@_dataclass(init=False, frozen=True)
class TagSearch:

	url: URLs.SplitResult

	__stored_url_override_query = dict(page=None, utf8=None)
	__search_override_query = dict(utf8='✓')
	__query_sort_override_weights = {
		'utf8': -11,
		'query[name]': -2,
		'query[type]': -1,
		'view_adult': 10,
		'page': 11,
	}

	def __init__(self, url: _u[_str, URLs.SplitResult], view_adult=True):
		super(TagSearch, self).__init__()

		url_str: str = (
			url.geturl() if isinstance(url, URLs.SplitResult)
			else url
		)
		assert isinstance(url_str, str), f"URL must be a string: {url_str}"
		if url_str.startswith('?'):
			url_str = URLs.tag_search_root + url_str  # turn just a query to a rel url

		url_split = URLs.split(url_str, unquote=False, to_abs=True)
		assert url_split.path.startswith(URLs.tag_search_root), f"Not a tag search page: {url}"

		url_split = URLs.override_query(
			url_split, quote_mode=0, query_sort_key_f=self.__query_sort_key,
			view_adult='true' if view_adult else None,
			**self.__stored_url_override_query
		)
		object.__setattr__(self, "url", url_split)  # the way to go for frozen

	@classmethod
	def __tags_from_single_search_page(cls, page: BeautifulSoup):
		"""Parse a single search page for tags."""

		# page = BeautifulSoup(requests.get(url).text, parser)
		tag_ols = page.find_all('ol', class_='tag index group')
		assert len(tag_ols) == 1, f"Found {len(tag_ols)} tag lists"
		tag_ol: _bsTag = tag_ols[0]
		tag_lines = tag_ol.find_all('li')

		return (Tag.build_from_li(tag_li) for tag_li in tag_lines)

	@classmethod
	def __query_sort_key(cls, i_key_val: _tpl[int, _str, _tA]):
		i, key, val = i_key_val
		return cls.__query_sort_override_weights.get(key, 0), i

	def page_urls(self, n: int, skip_first=False):
		return [
			URLs.override_query(
				self.url, query_sort_key_f=self.__query_sort_key,
				page=x if x > 1 else None, **self.__search_override_query,
			).geturl()
			for x in range(
				2 if skip_first else 1,
				max(1, n) + 1
			)
		]

	@classmethod
	def __detect_pages_number(cls, pager_ol: _bsTag):
		lis: _l[_bsTag] = pager_ol.find_all('li')
		last_li = None
		while lis:
			last_li = lis.pop()
			if 'next' in last_li.get('class', []):
				last_li = None
				continue
			break
		assert last_li is not None, 'Something weird happened: pager found, pages - not'
		n_str: str = last_li.a.text
		n_str = n_str.strip()
		return int(n_str)

	def load_tags(self, cache=True):
		"""Load all the tags from all the pages for the given search url."""
		res = TagSet(
			name=URLs.override_query(
				self.url, keep_blank_values=False, quote_mode=0,
				query_sort_key_f=self.__query_sort_key,
				**self.__stored_url_override_query
			).query
		)

		def dummy(tag_set: TagSet):
			return tag_set

		def cache_and_return(tag_set: TagSet):
			cache_dir = Paths.tags_cache_dir / 'from_search'
			if not cache_dir.exists():
				cache_dir.mkdir(parents=True)

			file_name = tag_set.name
			file_name_chars = set(file_name)
			placeholder = Paths.reserved_placeholder
			for reserved_char in Paths.reserved_chars:
				if reserved_char in file_name_chars:
					file_name = file_name.replace(reserved_char, placeholder)
			out_file = cache_dir / (file_name + '.txt')
			if out_file.is_reserved():
				raise OSError(
					errno.EPERM, 'Attempt to create a file with reserved special names',
					out_file
				)

			print(f'\nSaving cache file:\n\t{out_file}')
			with out_file.open('wt', encoding='UTF-8', newline='\n') as f:
				f.writelines(ln + '\n' for ln in tag_set.dumps(separator_line=_empty_str))

			return tag_set

		out_f = cache_and_return if cache else dummy

		first_url = URLs.override_query(
			self.url, page=None, query_sort_key_f=self.__query_sort_key,
			**self.__search_override_query
		).geturl()
		print(first_url)
		first_page_soup = BeautifulSoup(requests.get(first_url).text, parser)

		pagers = first_page_soup.find_all('ol', class_='pagination')
		if not pagers:
			# only a single page result:
			res.update(self.__tags_from_single_search_page(first_page_soup))
			return out_f(res)

		assert len(pagers) == 1, f'Multiple pagers found on search page: {first_url}'
		n = self.__detect_pages_number(pagers[0])
		assert n > 1, f'A really weird case: pager found, with pages, but biggest is {n}: {first_url}'

		print(f'Pages: {n}\n')
		page_soups = [first_page_soup, ]
		other_pages_content = _get_pages_async(
			self.page_urls(n, skip_first=True), print_urls=True
		)
		for url, code, html in other_pages_content:
			assert code == 200, f"Server error {code}: {url}"
		print(f'\nLoaded: {len(other_pages_content) + 1}\n')

		page_soups.extend(
			BeautifulSoup(html, parser)
			for url, code, html in other_pages_content
		)

		res.update(
			chain(*map(self.__tags_from_single_search_page, page_soups))
		)
		return out_f(res)


if __name__ == '__main__':
	tags = TagSet(name='QQQ')
