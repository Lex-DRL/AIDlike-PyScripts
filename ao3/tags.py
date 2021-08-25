# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t
from pathlib import Path
from enum import Enum
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
from .__paths import _StaticDataClass


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


# def init_tag_cleanup_dec(class_obj: _t.Type[_t.NamedTuple]):
# 	def new_instance(*args, **kwargs):
# 		if len(args) > 4:
# 			args_list = list(args)
# 			args_list[4] = clean_url(args[4])
# 			args = tuple(args_list)
# 		if 'url' in kwargs:
# 			kwargs['url'] = clean_url(kwargs['url'])
# 		return class_obj(*args, **kwargs)
#
# 	return new_instance


_tag_id_items = 3  # how many tag items from start are used for hash / == check
_unknown_tag_usage = -1  # default <usage> value


_type = type
NoneType = type(None)


# @init_tag_cleanup_dec
class Tag(_t.NamedTuple):
	"""
	NamedTuple representing a tag.

	Only first 3 items (type/name/canon) are used for any comparisons and hashing,
	optional items are ignored.
	Therefore:
		* `(type, name) != tag_instance`
		* `(type, name, canonical) == tag_instance`
		* `(type, name, canonical, usages, url) != tag_instance`

	So beware about it. Since, if you slice it, the newly created regular tuple
	is no longer equal to the tag instance, because it contains all the items and
	the instance itself is "represented" with just two in equality check.

	Similarly, if you have two tag instances with different values in optional
	items and you make a set of them / dict with them as keys - then only one
	of them will get into the set.
	"""
	type: _t.Union[None, TagType, str]
	name: str
	canonical: _t.Optional[bool] = False
	usages: int = _unknown_tag_usage
	url: str = None
	date: _t.Optional[dt] = None

	# noinspection PyAttributeOutsideInit
	@property
	def id(self):
		"""The actual value the tag is represented as during hashing/equality check."""
		return self[:_tag_id_items]

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
	def _clean_args(cls, calling_method: str, *args):
		"""Perform check on input arguments and auto-clean them if possible."""

		type, name, canonical, usages, url, date, *extras = args

		url: str = URLs.unsplit(URLs.split(url, to_abs=False))

		if canonical is not None:
			canonical = bool(canonical)

		if usages is None:
			usages = _unknown_tag_usage

		assert name and isinstance(name, str), (
			f'Invalid tag name passed to {cls.__name__}.{calling_method}(): {repr(name)}'
		)
		assert isinstance(type, (NoneType, TagType, str)), (
			f'Wrong type for tag <{name}>.{calling_method}(): {repr(type)}'
		)
		assert isinstance(canonical, (NoneType, bool)), (
			f'Wrong canonical state for tag <{name}>.{calling_method}(): {repr(canonical)}'
		)
		assert isinstance(usages, int), (
			f'Wrong usages for tag <{name}>.{calling_method}(): {repr(usages)}'
		)
		assert not url or isinstance(url, str) and url.startswith(URLs.tag_root), (
			f'Wrong URL for tag <{name}>.{calling_method}(): {repr(url)}'
		)

		type: _t.Union[None, TagType, str] = type
		canonical: _t.Optional[bool] = canonical
		date: _t.Optional[dt] = cls._clean_date(calling_method, date, name)
		if date is None and usages > -1:
			date = dt.now()

		return type, name, canonical, usages, url, date

	# noinspection PyShadowingBuiltins
	@classmethod
	def new_instance(
		cls,
		type: _t.Union[None, TagType, str],
		name: str,
		canonical: _t.Optional[bool] = False,
		usages: _t.Optional[int] = _unknown_tag_usage,
		url: _t.Optional[str] = None,
		date: _t.Optional[dt] = None,
	):
		"""
		Use this constructor method instead of just `Tag()`, because it performs
		some extra arguments check/cleanup.
		"""
		type, name, canonical, usages, url, date = cls._clean_args(
			'new_instance',
			type, name, canonical, usages, url, date
		)

		return cls(type, name, canonical=canonical, usages=usages, url=url, date=date)

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
			tag_type, a.text, canonical=canonical, url=a.get('href')
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
		type, name, canonical, usages, url, date, *left = items
		return name, type, canonical, usages, url, date

	# noinspection PyShadowingBuiltins
	def dumps(self):
		"""Dump tag object to a string representation for saving to a file."""

		type, name, canonical, usages, url, date = self._clean_args('dumps', *self)

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

		return self.reorder_to_dump(
			id + val for id, val in zip(
				_TagDumpConfig.dump_id,
				(type, name, canonical_s, usages_s, url, date_s),
			)
		)


# noinspection PyTypeChecker
class _TagDumpConfig(_StaticDataClass):
	"""Constants related to dumped tag format."""

	date_format: str = '%Y.%m.%d-%H:%M:%S|%Z'
	dump_id = Tag(
		type='-Tp:', name='-Tag:', canonical='-Canon:',
		usages='-Use:', url='-URL:', date='-Dt:',
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
		canonical={
			None: '',
			True: '+',
			False: '-',
		},
		usages=None,
		url=None,
		date=None,
	)


class __TagIO(object):
	"""Base class with common methods for loading/saving tags."""

	def _load_from_search_page(self, url: str):
		"""Parse a single search page for tags."""
		url_split = URLs.split(url)
		assert url_split.path.startswith(URLs.tag_search_root), f"Not a tag search page: {url}"
		url = URLs.unsplit(url_split)

		page = BeautifulSoup(requests.get(url).text, parser)
		tag_ols = page.find_all('ol', class_='tag index group')
		assert len(tag_ols) == 1, f"Found {len(tag_ols)} tag lists"
		tag_ol: _bsTag = tag_ols[0]
		tag_lines = tag_ol.find_all('li')

		return (Tag.build_from_li(tag_li) for tag_li in tag_lines)


class TagSet(_t.Set[Tag], __TagIO):

	name: str = ''

	def __init__(self, *args, name: str = ''):
		super(TagSet, self).__init__(*args)
		if name:
			self.name = name

	def _load_from_search_page(self, url: str):
		self.update(
			super(TagSet, self)._load_from_search_page(url)
		)
		return self

	def __repr__(self):
		res = super(TagSet, self).__repr__()
		if self.name:
			res = res.replace('(', f'({repr(self.name)}: ', 1)
		return res
