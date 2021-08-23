# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t
from pathlib import Path
from enum import Enum

import requests
# noinspection PyProtectedMember
from bs4 import (
	BeautifulSoup,
	Tag as _bsTag
)

from .__url import URLs, _StaticDataClass

module_dir = Path(__file__).parent

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


# @init_tag_cleanup_dec
class Tag(_t.NamedTuple):
	"""
	NamedTuple representing a tag.

	Only first two items (type/name) are used for any comparisons and hashing,
	optional items are ignored.
	Therefore:
		* `(type, name) == tag_instance`
		* `(type, name, canonical) != tag_instance`
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

	def __eq__(self, other):
		if isinstance(other, Tag):
			other = other[:_tag_id_items]
		return self[:_tag_id_items] == other

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return hash(self[:_tag_id_items])

	# noinspection PyShadowingBuiltins
	@classmethod
	def new_instance(
		cls,
		type: _t.Union[None, TagType, str],
		name: str,
		canonical: _t.Optional[bool] = False,
		usages: _t.Optional[int] = _unknown_tag_usage,
		url: _t.Optional[str] = None,
	):
		"""
		Use this constructor method instead of just `Tag()`, because it performs
		some extra arguments check/cleanup.
		"""
		url: str = URLs.unsplit(URLs.split(url, to_abs=False))
		assert url.startswith(URLs.tag_root) or not url, f'Invalid tag URL: {url}'
		if canonical is not None:
			canonical = bool(canonical)
		if usages is None:
			usages = _unknown_tag_usage

		assert isinstance(type, (_type(None), TagType, str)), f'Wrong <type> item: {type}'
		assert name and isinstance(name, str), f'Wrong <name> item: {name}'
		assert isinstance(usages, int), f'Wrong <usages> item: {usages}'
		return cls(type, name, canonical=canonical, usages=usages, url=url)

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

	# noinspection PyShadowingBuiltins
	def dumps(self):
		"""Dump tag object to a string representation for saving to a file."""

		type, name, canonical, usages, url = self
		dump_maps = _TagDumpConfig.dump_map
		if not type:
			type = ''
		if isinstance(type, TagType):
			# noinspection PyTypeChecker
			type = dump_maps.type[type]
		assert isinstance(type, str), f'Wrong type for <{name}> tag: {repr(type)}'
		type_s: str = type

		assert name and isinstance(name, str), f'Invalid tag name: {repr(name)}'

		assert isinstance(canonical, (_type(None), bool)), f'Invalid canonical state for <{name}> tag: {repr(canonical)}'
		# noinspection PyUnresolvedReferences
		canonical_s: str = dump_maps.canonical[canonical]

		if usages is None or usages < 0:
			usages = -1
		assert isinstance(usages, int), f'Invalid usage count  for <{name}> tag: {repr(usages)}'
		usages_s: str = '' if usages < 0 else str(usages)

		if not url:
			url = ''
		assert isinstance(url, str)
		url: str = URLs.unsplit(URLs.split(url, to_abs=False))

		return _TagDumpConfig.reorder_dump(
			id + val for id, val in zip(
				_TagDumpConfig.dump_id,
				(type_s, name, canonical_s, usages_s, url),
			)
		)


# noinspection PyTypeChecker
class _TagDumpConfig(_StaticDataClass):
	"""Constants related to dumped tag format."""

	dump_id = Tag(type='-Tp:', name='-Tag:', canonical='-Canon:', usages='-Use:', url='-URL:')
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
		url=None
	)

	@classmethod
	def reorder_dump(cls, items: _t.Iterable):
		"""Reorder tag elements from pythonic to dumped order."""
		# noinspection PyShadowingBuiltins
		type, name, canonical, usages, url, *left = items
		return name, type, canonical, usages, url


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
