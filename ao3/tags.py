# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

from enum import Enum
from itertools import chain
from collections import OrderedDict
from dataclasses import dataclass as _dataclass
from datetime import (
	datetime as dt,
	timezone as tz,
)

import requests
# noinspection PyProtectedMember
from bs4 import (
	BeautifulSoup,
	Tag as _bsTag
)

from .__url import URLs
from .__paths import _StaticDataClass, Paths


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


_defaults_none = (None, _f_none)
_defaults_str = ('', str)
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
_t_tag_ref = _t.Set[str]
_unknown_tag_usage: int = _tag_defaults['usages'][0]  # default <usage> value
_type = type
NoneType = type(None)


class Tag(_t.NamedTuple):
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
	type: _t.Union[None, TagType, str]
	name: str

	url_token: str = _tag_defaults['url_token'][0]

	canonical: _t.Optional[bool] = _tag_defaults['canonical'][0]
	usages: int = _unknown_tag_usage
	date: _t.Optional[dt] = _tag_defaults['date'][0]

	synonyms: _t_tag_ref = _tag_defaults['synonyms'][0]
	parents: _t_tag_ref = _tag_defaults['parents'][0]
	children: _t_tag_ref = _tag_defaults['children'][0]
	subtags: _t_tag_ref = _tag_defaults['subtags'][0]
	metatags: _t_tag_ref = _tag_defaults['metatags'][0]

	# noinspection PyAttributeOutsideInit
	@property
	def id(self):
		"""The actual value the tag is represented as during hashing/equality check."""
		return self.name, self.url_token

	def __eq__(self, other):
		return self.id == (
			other.id if isinstance(other, Tag) else other
		)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return hash(self.id)

	@classmethod
	def _clean_date(cls, calling_method: str, date: _t.Optional[dt], name: str = None):
		"""
		Part of `_clean_args()` that checks only date argument
		(it might be needed to check it separately).
		"""
		tag_part = cls.__name__ if name is None else f'for tag <{name}>'
		assert isinstance(date, (NoneType, dt)), (
			f'Wrong date {tag_part}.{calling_method}(): {repr(date)}'
		)
		date: _t.Optional[dt] = date
		return date

	# noinspection PyShadowingBuiltins
	@classmethod
	def _clean_args(
		cls,
		calling_method: str,
		*args,
		url_token_already_clean=False,  # we need to know whether it's already not an URL
		**kwargs
	):
		"""Perform check on input arguments and auto-clean them if possible."""

		def _args_gen(args_seq: _t.Iterable, kwargs_dict: dict):
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
		def _clean_ref(val, name: str, ref_name: str) -> _t_tag_ref:
			"""Prepare ref-field value to be passed to the constructor."""
			def _ensure_ref_item_type(item):
				assert isinstance(item, str), (
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

		if (
			url_token != _TagDumpConfig.token_match_name_indicator
			and not url_token_already_clean
		):
			# url_token = 'https://archiveofourown.org/tags/Admiral%20Anderson'
			# url_token = '/tags/Mass%20Effect%20Trilogy'
			# url_token = 'Mass Effect Trilogy'
			# url_token = 'Mass Effect Trilogy/works'
			url_token: str = URLs.split(url_token, unquote=True, to_abs=False).path
			if url_token.startswith(URLs.tag_root):
				url_token = url_token[URLs.tag_root_n:]
			url_token = url_token.split('/')[0]
			if url_token == name:
				url_token = _TagDumpConfig.token_match_name_indicator

		assert isinstance(url_token, str) and (
			not url_token
			or url_token == _TagDumpConfig.token_match_name_indicator
			or _TagDumpConfig.token_match_name_indicator not in url_token
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

		type: _t.Union[None, TagType, str] = type
		canonical: _t.Optional[bool] = canonical
		date: _t.Optional[dt] = cls._clean_date(calling_method, date, name)
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

		type: _t.Union[None, TagType, str],
		name: str,
		url_token: _t.Optional[str] = None,

		canonical: _t.Optional[bool] = False,
		usages: _t.Optional[int] = _unknown_tag_usage,
		date: _t.Optional[dt] = None,

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
	def date_str(cls, date: _t.Optional[dt]):
		clean_date = cls._clean_date('date_str', date)
		if clean_date is None:
			return ''
		return clean_date.strftime(_TagDumpConfig.date_format)

	@classmethod
	def date_from_str(cls, date_str: _t.Optional[str], in_timezone=None):
		if not date_str:
			return None
		return dt.strptime(date_str, _TagDumpConfig.date_format).astimezone(in_timezone)

	@classmethod
	def reorder_to_dump(cls, items: _t.Iterable):
		"""Reorder tag elements from tuple to dumped order."""
		# noinspection PyShadowingBuiltins
		type, name, url_token, canonical, usages, date, *left = items
		return name, url_token, type, canonical, usages, date

	# noinspection PyShadowingBuiltins
	def dumps(self) -> _t.Tuple[str, ...]:
		"""
		Dump tag object to a string representation for saving to a file.

		No trailing newline characters.
		"""

		(
			type, name, url_token, canonical, usages, date,
			synonyms, parents, children, subtags, metatags,
		) = self._clean_args(
			'dumps', *self,
			url_token_already_clean=True
		)

		dump_maps = _TagDumpConfig.dump_map

		if not type:
			type = ''
		if isinstance(type, TagType):
			# noinspection PyTypeChecker
			type: str = dump_maps.type[type]
		assert isinstance(type, str)

		# noinspection PyUnresolvedReferences
		canonical_s: str = dump_maps.canonical[canonical]

		if usages is None or usages < 0:
			usages = -1
		usages_s: str = '' if usages < 0 else str(usages)

		date_s = '' if date is None else self.date_str(date.astimezone(tz=tz.utc))

		id_val_pairs = self.reorder_to_dump(zip(
			_TagDumpConfig.dump_id,
			(type, name, url_token, canonical_s, usages_s, date_s),
		))
		return tuple(
			id + val for id, val in id_val_pairs
		)

	def sorting_key(self):
		"""A key for tags sort."""

		# noinspection PyShadowingBuiltins
		def type_string(type):
			if type is None:
				return ''
			if isinstance(type, str):
				return type
			assert isinstance(type, TagType)
			return f'{type.value}_{type.name}'

		def date_key(date: _t.Optional[dt]):
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
			None: '',
			True: '+',
			False: '-',
		},
	)


class TagSet(_t.Set[Tag]):

	name: str = ''

	def __init__(self, *args, name: str = ''):
		super(TagSet, self).__init__(*args)
		if name:
			self.name = name

	def __repr__(self):
		res = super(TagSet, self).__repr__()
		if self.name:
			res = res.replace('(', f'({repr(self.name)}: ', 1)
		return res

	def dumps(self, separator_line=''):
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

	def __init__(self, url: _t.Union[str, URLs.SplitResult], view_adult=True):
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
	def __query_sort_key(cls, i_key_val: _t.Tuple[int, str, _t.Any]):
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
		lis: _t.List[_bsTag] = pager_ol.find_all('li')
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

			out_file = cache_dir / (tag_set.name + '.txt')
			print(f'\nSaving cache file:\n\t{out_file}')
			with out_file.open('wt', encoding='UTF-8', newline='\n') as f:
				f.writelines(ln + '\n' for ln in tag_set.dumps(separator_line=''))

			return tag_set

		out_f = cache_and_return if cache else dummy

		def get_page_soup(url: str):
			print(url)
			return BeautifulSoup(requests.get(url).text, parser)

		first_url = URLs.override_query(
			self.url, page=None, query_sort_key_f=self.__query_sort_key,
			**self.__search_override_query
		).geturl()
		first_page_soup = get_page_soup(first_url)

		pagers = first_page_soup.find_all('ol', class_='pagination')
		if not pagers:
			# only a single page result:
			res.update(self.__tags_from_single_search_page(first_page_soup))
			return out_f(res)

		assert len(pagers) == 1, f'Multiple pagers found on search page: {first_url}'
		n = self.__detect_pages_number(pagers[0])
		assert n > 1, f'A really weird case: pager found, with pages, but biggest is {n}: {first_url}'

		other_page_soups = [
			get_page_soup(url)
			for url in self.page_urls(n, skip_first=True)
		]

		res.update(
			chain(*(
				self.__tags_from_single_search_page(page_soup)
				for page_soup in chain([first_page_soup], other_page_soups)
			))
		)
		return out_f(res)


if __name__ == '__main__':
	tags = TagSet(name='QQQ')
